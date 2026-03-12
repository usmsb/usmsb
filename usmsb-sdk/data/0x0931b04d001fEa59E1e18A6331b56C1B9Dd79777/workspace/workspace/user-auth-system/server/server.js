const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 3001;
const DATA_FILE = path.join(__dirname, 'data', 'users.json');

// Middleware
app.use(cors());
app.use(bodyParser.json());

// 初始化数据文件
if (!fs.existsSync(DATA_FILE)) {
  fs.writeFileSync(DATA_FILE, JSON.stringify([]));
}

// 读取用户数据
function readUsers() {
  try {
    const data = fs.readFileSync(DATA_FILE, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    return [];
  }
}

// 保存用户数据
function saveUsers(users) {
  fs.writeFileSync(DATA_FILE, JSON.stringify(users, null, 2));
}

// 注册接口
app.post('/api/register', (req, res) => {
  const { username, password, email } = req.body;
  
  if (!username || !password || !email) {
    return res.status(400).json({ success: false, message: '请填写所有字段' });
  }
  
  const users = readUsers();
  
  // 检查用户名是否已存在
  if (users.find(u => u.username === username)) {
    return res.status(400).json({ success: false, message: '用户名已存在' });
  }
  
  // 检查邮箱是否已存在
  if (users.find(u => u.email === email)) {
    return res.status(400).json({ success: false, message: '邮箱已被注册' });
  }
  
  // 创建新用户
  const newUser = {
    id: Date.now(),
    username,
    password, // 注意：生产环境应该加密密码
    email,
    createdAt: new Date().toISOString()
  };
  
  users.push(newUser);
  saveUsers(users);
  
  res.json({ success: true, message: '注册成功', user: { id: newUser.id, username: newUser.username, email: newUser.email } });
});

// 登录接口
app.post('/api/login', (req, res) => {
  const { username, password } = req.body;
  
  if (!username || !password) {
    return res.status(400).json({ success: false, message: '请填写用户名和密码' });
  }
  
  const users = readUsers();
  const user = users.find(u => u.username === username && u.password === password);
  
  if (!user) {
    return res.status(401).json({ success: false, message: '用户名或密码错误' });
  }
  
  res.json({ 
    success: true, 
    message: '登录成功', 
    user: { id: user.id, username: user.username, email: user.email } 
  });
});

// 获取所有用户（仅用于调试）
app.get('/api/users', (req, res) => {
  const users = readUsers();
  // 隐藏密码
  const safeUsers = users.map(u => ({ ...u, password: '***' }));
  res.json(safeUsers);
});

app.listen(PORT, () => {
  console.log(`✅ 后端服务器运行在 http://localhost:${PORT}`);
});
