const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 3001;
const DATA_FILE = path.join(__dirname, 'users.json');

// Middleware
app.use(cors());
app.use(bodyParser.json());

// Initialize users.json if not exists
if (!fs.existsSync(DATA_FILE)) {
  fs.writeFileSync(DATA_FILE, JSON.stringify([]));
}

// Helper: Read users
function readUsers() {
  const data = fs.readFileSync(DATA_FILE, 'utf8');
  return JSON.parse(data || '[]');
}

// Helper: Write users
function writeUsers(users) {
  fs.writeFileSync(DATA_FILE, JSON.stringify(users, null, 2));
}

// Register endpoint
app.post('/api/register', (req, res) => {
  const { username, password, email } = req.body;
  
  if (!username || !password || !email) {
    return res.status(400).json({ success: false, message: 'All fields are required' });
  }

  const users = readUsers();
  
  // Check if user exists
  if (users.find(u => u.username === username)) {
    return res.status(400).json({ success: false, message: 'Username already exists' });
  }
  
  if (users.find(u => u.email === email)) {
    return res.status(400).json({ success: false, message: 'Email already exists' });
  }

  // Add new user
  const newUser = {
    id: Date.now(),
    username,
    password, // In production, hash the password!
    email,
    createdAt: new Date().toISOString()
  };
  
  users.push(newUser);
  writeUsers(users);
  
  res.json({ success: true, message: 'Registration successful', user: { username, email } });
});

// Login endpoint
app.post('/api/login', (req, res) => {
  const { username, password } = req.body;
  
  if (!username || !password) {
    return res.status(400).json({ success: false, message: 'Username and password are required' });
  }

  const users = readUsers();
  const user = users.find(u => u.username === username && u.password === password);
  
  if (!user) {
    return res.status(401).json({ success: false, message: 'Invalid username or password' });
  }

  res.json({ 
    success: true, 
    message: 'Login successful', 
    user: { 
      id: user.id,
      username: user.username, 
      email: user.email 
    } 
  });
});

// Get all users (for testing)
app.get('/api/users', (req, res) => {
  const users = readUsers();
  // Don't return passwords
  const safeUsers = users.map(u => ({ id: u.id, username: u.username, email: u.email, createdAt: u.createdAt }));
  res.json(safeUsers);
});

app.listen(PORT, () => {
  console.log(`Backend server running on http://localhost:${PORT}`);
});
