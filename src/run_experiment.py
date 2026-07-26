#!/usr/bin/env python3
"""Reduced-QM9 reproduction of the discrete Expanding Flow Maps claim.

The implementation deliberately keeps the public benchmark and outcome metrics
while shrinking the transformer and split. It supports an expanding model with
per-node local times and learned gap insertions, a fixed-canvas control, and a
two-step distilled map / insertion-disabled ablation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import torch.distributed as dist
import torch.nn as nn
import torch.nn.functional as F
from rdkit import Chem, RDLogger
from torch.nn.parallel import DistributedDataParallel as DDP

RDLogger.DisableLog("rdApp.*")

ATOM_TYPES = (6, 7, 8, 9)
ATOM_TO_CLASS = {z: i for i, z in enumerate(ATOM_TYPES)}
BOND_TO_CLASS = {
    Chem.BondType.SINGLE: 1,
    Chem.BondType.DOUBLE: 2,
    Chem.BondType.TRIPLE: 3,
    Chem.BondType.AROMATIC: 4,
}
MAX_NODES = 9
QM9_URL = "https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/qm9.csv"


def rank0() -> bool:
    return int(os.environ.get("RANK", "0")) == 0


def log(message: str) -> None:
    if rank0():
        print(message, flush=True)


def setup_dist() -> tuple[int, int, int, torch.device]:
    rank = int(os.environ.get("RANK", "0"))
    world = int(os.environ.get("WORLD_SIZE", "1"))
    local = int(os.environ.get("LOCAL_RANK", "0"))
    torch.cuda.set_device(local)
    device = torch.device(f"cuda:{local}")
    if world > 1:
        dist.init_process_group("nccl", device_id=device)
    return rank, world, local, device


def download_qm9() -> Path:
    cache = Path("/tmp/efm-qm9")
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / "qm9.csv"
    if rank0() and (not target.exists() or target.stat().st_size < 20_000_000):
        log(f"DATA download={QM9_URL}")
        urllib.request.urlretrieve(QM9_URL, target)
    if dist.is_initialized():
        dist.barrier()
    return target


def smiles_to_graph(smiles: str) -> tuple[np.ndarray, np.ndarray, int] | None:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    mol = Chem.RemoveHs(mol)
    atoms = [a.GetAtomicNum() for a in mol.GetAtoms()]
    if not 1 <= len(atoms) <= MAX_NODES or any(z not in ATOM_TO_CLASS for z in atoms):
        return None
    # Random order during training is supplied later; canonical graph is stored here.
    nodes = np.full(MAX_NODES, -1, dtype=np.int64)
    edges = np.zeros((MAX_NODES, MAX_NODES), dtype=np.int64)
    nodes[: len(atoms)] = [ATOM_TO_CLASS[z] for z in atoms]
    for bond in mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        c = BOND_TO_CLASS.get(bond.GetBondType(), 0)
        edges[i, j] = edges[j, i] = c
    return nodes, edges, len(atoms)


def load_split(cfg: dict) -> tuple[dict[str, torch.Tensor], list[str]]:
    path = download_qm9()
    total = cfg["train_size"] + cfg["valid_size"] + cfg["test_size"]
    records: list[tuple[np.ndarray, np.ndarray, int, str]] = []
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        smiles_key = "smiles"
        for row in reader:
            parsed = smiles_to_graph(row[smiles_key])
            if parsed is not None:
                nodes, edges, n = parsed
                can = Chem.MolToSmiles(Chem.MolFromSmiles(row[smiles_key]), canonical=True)
                records.append((nodes, edges, n, can))
                if len(records) >= total:
                    break
    rng = random.Random(20260726)
    rng.shuffle(records)
    records = records[:total]
    nodes = torch.from_numpy(np.stack([r[0] for r in records]))
    edges = torch.from_numpy(np.stack([r[1] for r in records]))
    counts = torch.tensor([r[2] for r in records], dtype=torch.long)
    start = cfg["train_size"] + cfg["valid_size"]
    log(
        f"DATA source=public_QM9 rows={len(records)} split="
        f"{cfg['train_size']}/{cfg['valid_size']}/{cfg['test_size']} "
        f"sha256={hashlib.sha256(path.read_bytes()).hexdigest()[:16]}"
    )
    return {"nodes": nodes, "edges": edges, "counts": counts}, [r[3] for r in records[start:]]


class GraphBlock(nn.Module):
    def __init__(self, hidden: int, heads: int):
        super().__init__()
        self.heads = heads
        self.dim = hidden // heads
        self.norm1 = nn.LayerNorm(hidden)
        self.qkv = nn.Linear(hidden, 3 * hidden)
        self.edge_bias = nn.Linear(hidden, heads)
        self.out = nn.Linear(hidden, hidden)
        self.norm2 = nn.LayerNorm(hidden)
        self.ff = nn.Sequential(
            nn.Linear(hidden, 4 * hidden), nn.SiLU(), nn.Linear(4 * hidden, hidden)
        )
        self.edge_update = nn.Sequential(
            nn.Linear(3 * hidden, hidden), nn.SiLU(), nn.Linear(hidden, hidden)
        )

    def forward(self, x: torch.Tensor, e: torch.Tensor, mask: torch.Tensor):
        b, n, h = x.shape
        z = self.norm1(x)
        q, k, v = self.qkv(z).chunk(3, dim=-1)
        q = q.view(b, n, self.heads, self.dim).transpose(1, 2)
        k = k.view(b, n, self.heads, self.dim).transpose(1, 2)
        v = v.view(b, n, self.heads, self.dim).transpose(1, 2)
        score = torch.matmul(q, k.transpose(-1, -2)) / math.sqrt(self.dim)
        score = score + self.edge_bias(e).permute(0, 3, 1, 2)
        key_mask = mask[:, None, None, :]
        score = score.masked_fill(~key_mask, -1e4)
        attn = torch.softmax(score, dim=-1)
        y = torch.matmul(attn, v).transpose(1, 2).reshape(b, n, h)
        x = x + self.out(y) * mask.unsqueeze(-1)
        x = x + self.ff(self.norm2(x)) * mask.unsqueeze(-1)
        xi = x[:, :, None, :].expand(-1, -1, n, -1)
        xj = x[:, None, :, :].expand(-1, n, -1, -1)
        e = e + self.edge_update(torch.cat([e, xi, xj], dim=-1))
        return x, e


class GraphDenoiser(nn.Module):
    def __init__(self, cfg: dict):
        super().__init__()
        h = cfg["hidden_dim"]
        self.method = cfg["method"]
        self.node_in = nn.Linear(5, h)
        self.edge_in = nn.Linear(5, h)
        self.time_in = nn.Sequential(nn.Linear(4, h), nn.SiLU(), nn.Linear(h, h))
        self.blocks = nn.ModuleList([GraphBlock(h, cfg["heads"]) for _ in range(cfg["layers"])])
        self.node_out = nn.Linear(h, 5)
        self.edge_out = nn.Linear(h, 5)
        self.count_head = nn.Sequential(nn.Linear(h, h), nn.SiLU(), nn.Linear(h, MAX_NODES))
        self.gap_head = nn.Sequential(nn.Linear(h, h), nn.SiLU(), nn.Linear(h, 1))
        self.empty_token = nn.Parameter(torch.randn(h) * 0.02)

    def forward(
        self,
        node_latent: torch.Tensor,
        edge_latent: torch.Tensor,
        active: torch.Tensor,
        local_t: torch.Tensor,
        global_s: torch.Tensor,
        global_t: torch.Tensor,
    ):
        b, n, _ = node_latent.shape
        x = self.node_in(node_latent)
        e = self.edge_in(edge_latent)
        gt = global_t[:, None].expand(-1, n)
        gs = global_s[:, None].expand(-1, n)
        tf = torch.stack([local_t, gt, gs, gt - gs], dim=-1)
        x = x + self.time_in(tf)
        safe_mask = active.clone()
        no_active = ~safe_mask.any(dim=1)
        safe_mask[no_active, 0] = True
        x[no_active, 0] = self.empty_token
        for block in self.blocks:
            x, e = block(x, e, safe_mask)
        denom = safe_mask.sum(1, keepdim=True).clamp_min(1)
        pooled = (x * safe_mask.unsqueeze(-1)).sum(1) / denom
        count_logits = self.count_head(pooled)
        gap_rate = F.softplus(self.gap_head(x).squeeze(-1)) + 1e-4
        return self.node_out(x), self.edge_out(e), count_logits, gap_rate


def permute_batch(nodes, edges, counts, generator):
    b = nodes.shape[0]
    out_n = nodes.clone()
    out_e = edges.clone()
    for k in range(b):
        n = int(counts[k])
        p = torch.randperm(n, generator=generator)
        out_n[k, :n] = nodes[k, p]
        out_e[k, :n, :n] = edges[k, :n, :n][p][:, p]
    return out_n, out_e


def make_training_state(nodes, edges, counts, method, device, generator):
    b = nodes.shape[0]
    t = torch.rand(b, device=device).clamp_(1e-3, 1.0)
    idx = torch.arange(MAX_NODES, device=device)[None, :]
    present = idx < counts[:, None]
    if method == "expanding":
        u = torch.rand((b, MAX_NODES), device=device)
        insertion_t = u.square()  # alpha(t)=sqrt(t), paper's r=0.5 schedule.
        active = present & (insertion_t <= t[:, None])
        local = ((t[:, None] - insertion_t) / (1 - insertion_t).clamp_min(1e-3)).clamp(0, 1)
        local = local * active
        clean_node = F.one_hot(nodes.clamp_min(0), 5).float()
    else:
        active = torch.ones_like(present)
        local = t[:, None].expand(-1, MAX_NODES)
        fixed_nodes = torch.where(present, nodes, torch.full_like(nodes, 4))
        clean_node = F.one_hot(fixed_nodes, 5).float()
    clean_edge = F.one_hot(edges, 5).float()
    node_noise = torch.randn(clean_node.shape, device=device, generator=generator)
    edge_noise = torch.randn(clean_edge.shape, device=device, generator=generator)
    edge_local = torch.minimum(local[:, :, None], local[:, None, :])
    if method == "fixed":
        edge_local = t[:, None, None].expand(-1, MAX_NODES, MAX_NODES)
    node_latent = local[..., None] * clean_node + (1 - local[..., None]) * node_noise
    edge_latent = edge_local[..., None] * clean_edge + (1 - edge_local[..., None]) * edge_noise
    return t, active, local, node_latent, edge_latent, present


def loss_batch(model, nodes, edges, counts, cfg, device, generator):
    t, active, local, xn, xe, present = make_training_state(
        nodes, edges, counts, cfg["method"], device, generator
    )
    zeros = torch.zeros_like(t)
    node_logits, edge_logits, count_logits, gap_rate = model(xn, xe, active, local, t, t)
    node_target = nodes.clamp_min(0)
    if cfg["method"] == "fixed":
        node_target = torch.where(present, nodes, torch.full_like(nodes, 4))
        node_mask = torch.ones_like(present)
    else:
        node_mask = active
    node_loss = F.cross_entropy(node_logits[node_mask], node_target[node_mask])
    edge_mask = node_mask[:, :, None] & node_mask[:, None, :]
    eye = torch.eye(MAX_NODES, device=device, dtype=torch.bool)[None]
    edge_mask &= ~eye
    edge_loss = F.cross_entropy(edge_logits[edge_mask], edges[edge_mask])
    count_loss = F.cross_entropy(count_logits, counts - 1)
    if cfg["method"] == "expanding":
        missing = (present & ~active).sum(1).float()
        pred_total_rate = (gap_rate * active).sum(1)
        pred_total_rate = torch.where(active.any(1), pred_total_rate, gap_rate[:, 0])
        insert_loss = (pred_total_rate - missing * torch.log(pred_total_rate + 1e-8)).mean()
    else:
        insert_loss = torch.zeros((), device=device)
    total = node_loss + 5.0 * edge_loss + 0.5 * count_loss + 0.2 * insert_loss
    return total, (node_loss, edge_loss, count_loss, insert_loss)


def train_model(cfg, data, device, rank, world, seed_offset=0):
    seed = cfg["seed"] + seed_offset
    torch.manual_seed(seed + rank)
    model = GraphDenoiser(cfg).to(device)
    if world > 1:
        # The fixed control intentionally never uses the insertion-only parameters.
        model = DDP(model, device_ids=[device.index], find_unused_parameters=True)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg["learning_rate"], weight_decay=1e-12)
    warmup = min(1000, cfg["train_steps"] // 10)
    ntrain = cfg["train_size"]
    gen = torch.Generator(device=device).manual_seed(seed + 1009 * rank)
    cpu_gen = torch.Generator().manual_seed(seed + 7919 * rank)
    start = time.time()
    ema = None
    model.train()
    for step in range(1, cfg["train_steps"] + 1):
        ids = torch.randint(0, ntrain, (cfg["batch_size_per_gpu"],), generator=cpu_gen)
        nodes = data["nodes"][ids]
        edges = data["edges"][ids]
        counts = data["counts"][ids]
        nodes, edges = permute_batch(nodes, edges, counts, cpu_gen)
        nodes, edges, counts = nodes.to(device), edges.to(device), counts.to(device)
        if step == 1:
            log("DEBUG_STAGE batch_on_device")
        opt.zero_grad(set_to_none=True)
        loss, parts = loss_batch(model, nodes, edges, counts, cfg, device, gen)
        if step == 1:
            log("DEBUG_STAGE forward_and_loss")
        loss.backward()
        if step == 1:
            log("DEBUG_STAGE backward")
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scale = min(1.0, step / warmup)
        for group in opt.param_groups:
            group["lr"] = cfg["learning_rate"] * scale
        opt.step()
        if rank0() and (step == 1 or step % 500 == 0):
            elapsed = time.time() - start
            log(
                f"TRAIN step={step}/{cfg['train_steps']} loss={loss.item():.4f} "
                f"node={parts[0].item():.4f} edge={parts[1].item():.4f} "
                f"count={parts[2].item():.4f} insert={parts[3].item():.4f} "
                f"samples_per_s={step * cfg['batch_size_per_gpu'] * world / elapsed:.1f}"
            )
    raw = model.module if isinstance(model, DDP) else model
    if world > 1:
        for p in raw.parameters():
            dist.broadcast(p.data, src=0)
    return raw


@torch.no_grad()
def sample_graphs(model, cfg, steps, nsamples, device, insertion_mode=None):
    model.eval()
    all_nodes, all_edges, all_counts = [], [], []
    batch_size = 512
    generator = torch.Generator(device=device).manual_seed(cfg["seed"] * 100 + steps + 17)
    for begin in range(0, nsamples, batch_size):
        b = min(batch_size, nsamples - begin)
        if cfg["method"] == "fixed":
            active = torch.ones((b, MAX_NODES), dtype=torch.bool, device=device)
            count = torch.full((b,), MAX_NODES, dtype=torch.long, device=device)
        else:
            active = torch.zeros((b, MAX_NODES), dtype=torch.bool, device=device)
            count = torch.zeros((b,), dtype=torch.long, device=device)
        xn = torch.randn((b, MAX_NODES, 5), device=device, generator=generator)
        xe = torch.randn((b, MAX_NODES, MAX_NODES, 5), device=device, generator=generator)
        xe = (xe + xe.transpose(1, 2)) / 2
        local = torch.zeros((b, MAX_NODES), device=device)
        for k in range(steps):
            s = torch.full((b,), k / steps, device=device)
            t = torch.full((b,), (k + 1) / steps, device=device)
            nl, el, cl, gap_rate = model(xn, xe, active, local, s, t)
            if cfg["method"] == "expanding":
                predicted_final = cl.argmax(-1) + 1
                if insertion_mode == "disabled":
                    # Mechanism ablation: all nine noisy nodes are exposed at the first jump.
                    target_count = torch.full_like(predicted_final, MAX_NODES)
                elif insertion_mode == "oracle":
                    target_count = predicted_final
                else:
                    alpha_s, alpha_t = math.sqrt(k / steps), math.sqrt((k + 1) / steps)
                    rho = (alpha_t - alpha_s) / max(1e-6, 1 - alpha_s)
                    remaining = (predicted_final - count).clamp_min(0)
                    lam = remaining.float() * rho
                    add = torch.poisson(lam, generator=generator).long()
                    target_count = torch.minimum(predicted_final, count + add)
                    if k == steps - 1:
                        target_count = predicted_final
                for q in range(b):
                    old, new = int(count[q]), int(target_count[q])
                    if new > old:
                        active[q, old:new] = True
                        local[q, old:new] = 0
                count = target_count
            progress = 1.0 / (steps - k)
            xn = (1 - progress) * xn + progress * torch.softmax(nl, -1)
            xe = (1 - progress) * xe + progress * torch.softmax(el, -1)
            xe = (xe + xe.transpose(1, 2)) / 2
            local = torch.where(active, (local + (1 - local) * progress), local)
        node_cls = xn.argmax(-1)
        edge_cls = xe.argmax(-1)
        edge_cls = torch.triu(edge_cls, diagonal=1)
        edge_cls = edge_cls + edge_cls.transpose(1, 2)
        if cfg["method"] == "fixed":
            count = (node_cls != 4).sum(1).clamp(1, MAX_NODES)
        all_nodes.append(node_cls.cpu())
        all_edges.append(edge_cls.cpu())
        all_counts.append(count.cpu())
    return torch.cat(all_nodes), torch.cat(all_edges), torch.cat(all_counts)


def graph_to_smiles(nodes: torch.Tensor, edges: torch.Tensor, count: int) -> str | None:
    rw = Chem.RWMol()
    for i in range(count):
        c = int(nodes[i])
        if c >= 4:
            return None
        rw.AddAtom(Chem.Atom(ATOM_TYPES[c]))
    bond_types = {
        1: Chem.BondType.SINGLE,
        2: Chem.BondType.DOUBLE,
        3: Chem.BondType.TRIPLE,
        4: Chem.BondType.AROMATIC,
    }
    try:
        for i in range(count):
            for j in range(i + 1, count):
                c = int(edges[i, j])
                if c:
                    rw.AddBond(i, j, bond_types[c])
        mol = rw.GetMol()
        Chem.SanitizeMol(mol)
        frags = Chem.GetMolFrags(mol, asMols=True)
        mol = max(frags, key=lambda m: m.GetNumAtoms())
        return Chem.MolToSmiles(mol, canonical=True)
    except Exception:
        return None


def calculate_fcd(generated: list[str], reference: list[str], device: str) -> float:
    try:
        from fcd_torch import FCD
        metric = FCD(device=device, n_jobs=8, batch_size=512)
        return float(metric(generated, reference))
    except Exception as exc:
        log(f"FCD_ERROR type={type(exc).__name__} message={str(exc)[:300]}")
        return float("nan")


def evaluate(model, cfg, reference_smiles, device):
    results = []
    insertion_mode = cfg.get("insertion", "learned")
    for steps in cfg["eval_steps"]:
        start = time.time()
        nodes, edges, counts = sample_graphs(
            model, cfg, steps, cfg["eval_samples"], device, insertion_mode
        )
        valid_smiles = []
        count_hist = [0] * MAX_NODES
        for x, e, n in zip(nodes, edges, counts):
            count_hist[int(n) - 1] += 1
            smi = graph_to_smiles(x, e, int(n))
            if smi is not None:
                valid_smiles.append(smi)
        validity = len(valid_smiles) / cfg["eval_samples"]
        uniqueness = len(set(valid_smiles)) / max(1, len(valid_smiles))
        # FCD accepts repeated generated molecules; cap only for runtime parity.
        fcd = calculate_fcd(valid_smiles, reference_smiles, str(device))
        result = {
            "method": cfg["name"],
            "family": cfg["method"],
            "seed": cfg["seed"],
            "steps": steps,
            "samples": cfg["eval_samples"],
            "validity": validity,
            "uniqueness": uniqueness,
            "fcd": fcd,
            "valid_count": len(valid_smiles),
            "unique_count": len(set(valid_smiles)),
            "node_count_histogram": count_hist,
            "eval_seconds": time.time() - start,
        }
        log("RESULT_JSON " + json.dumps(result, sort_keys=True))
        results.append(result)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    rank, world, local, device = setup_dist()
    wall_start = time.time()
    log(
        "CONFIG_JSON "
        + json.dumps(
            {
                **cfg,
                "backend": "kubernetes",
                "gpu_model": torch.cuda.get_device_name(device),
                "world_size": world,
                "torch": torch.__version__,
                "rdkit": Chem.rdBase.rdkitVersion,
            },
            sort_keys=True,
        )
    )
    data, reference = load_split(cfg)
    if world > 1:
        dist.barrier()
    model = train_model(cfg, data, device, rank, world)
    if world > 1:
        dist.barrier()
    if rank0():
        results = evaluate(model, cfg, reference, device)
        summary = {
            "status": "success",
            "experiment": cfg["name"],
            "results": results,
            "wall_seconds": time.time() - wall_start,
            "backend": "kubernetes",
            "gpu_model": torch.cuda.get_device_name(device),
            "allocated_gpus": world,
        }
        log("FINAL_SUMMARY_JSON " + json.dumps(summary, sort_keys=True))
    if world > 1:
        dist.destroy_process_group()


if __name__ == "__main__":
    main()
