const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const bcrypt = require('bcryptjs');

const app = express();
const PORT = 3001;
const DATA_FILE = path.join(__dirname, 'users.json');

app.use(cors());
app.use(express.json());

// 初始化数据文件
if (!fs.existsSync(DATA_FILE)) {
  fs.writeFileSync(DATA_FILE, '[]');
}

// 读取用户数据
const getUsers = () => {
  const data = fs.readFileSync(DATA_FILE, 'utf-8');
  return JSON.parse(data || '[]');
};

// 保存用户数据
const saveUsers = (users) => {
  fs.writeFileSync(DATA_FILE, JSON.stringify(users, null, 2));
};

// 注册
app.post('/api/register', async (req, res) => {
  const { username, password, email } = req.body;
  
  if (!username || !password || !email) {
    return res.status(400).json({ message: '请填写所有字段' });
  }
  
  const users = getUsers();
  
  if (users.find(u => u.username === username)) {
    return res.status(400).json({ message: '用户名已存在' });
  }
  
  if (users.find(u => u.email === email)) {
    return res.status(400).json({ message: '邮箱已被注册' });
  }
  
  const hashedPassword = await bcrypt.hash(password, 10);
  const newUser = {
    id: Date.now(),
    username,
    email,
    password: hashedPassword,
    createdAt: new Date().toISOString()
  };
  
  users.push(newUser);
  saveUsers(users);
  
  res.json({ message: '注册成功', user: { id: newUser.id, username: newUser.username, email: newUser.email } });
});

// 登录
app.post('/api/login', async (req, res) => {
  const { username, password } = req.body;
  
  if (!username || !password) {
    return res.status(400).json({ message: '请填写用户名和密码' });
  }
  
  const users = getUsers();
  const user = users.find(u => u.username === username);
  
  if (!user) {
    return res.status(401).json({ message: '用户名或密码错误' });
  }
  
  const isMatch = await bcrypt.compare(password, user.password);
  
  if (!isMatch) {
    return res.status(401).json({ message: '用户名或密码错误' });
  }
  
  res.json({ 
    message: '登录成功', 
    user: { id: user.id, username: user.username, email: user.email } 
  });
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
