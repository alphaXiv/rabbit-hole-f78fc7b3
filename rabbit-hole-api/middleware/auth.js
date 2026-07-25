const jwt = require('jsonwebtoken');

module.exports = function (req, res, next) {
  // 1. Get the token from the request header
  const token = req.header('x-auth-token');

  // 2. Check if no token exists
  if (!token) {
    return res.status(401).json({ error: 'No token, authorization denied' });
  }

  // 3. Verify the token is real and hasn't expired
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    
    // Attach the user payload (which contains their ID) to the request object
    req.user = decoded; 
    
    // Move on to the actual API route
    next(); 
  } catch (err) {
    res.status(401).json({ error: 'Token is not valid' });
  }
};