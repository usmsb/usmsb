import React, { useState } from 'react';
import './App.css';

function App() {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({ username: '', password: '', email: '' });
  const [message, setMessage] = useState('');
  const [user, setUser] = useState(null);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage('');

    const url = isLogin ? 'http://localhost:3001/api/login' : 'http://localhost:3001/api/register';
    
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      
      const data = await res.json();
      
      if (res.ok) {
        setMessage(data.message);
        if (isLogin) {
          setUser(data.user);
        } else {
          setIsLogin(true);
          setFormData({ username: '', password: '', email: '' });
        }
      } else {
        setMessage(data.message);
      }
    } catch (err) {
      setMessage('请求失败，请检查服务器是否运行');
    }
  };

  const handleLogout = () => {
    setUser(null);
    setFormData({ username: '', password: '', email: '' });
    setMessage('');
  };

  if (user) {
    return (
      <div className="App">
        <div className="container">
          <h1>欢迎回来！</h1>
          <div className="user-info">
            <p><strong>用户名：</strong>{user.username}</p>
            <p><strong>邮箱：</strong>{user.email}</p>
          </div>
          <button onClick={handleLogout} className="btn btn-secondary">退出登录</button>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      <div className="container">
        <h1>{isLogin ? '登录' : '注册'}</h1>
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            name="username"
            placeholder="用户名"
            value={formData.username}
            onChange={handleChange}
            required
          />
          <input
            type="email"
            name="email"
            placeholder="邮箱"
            value={formData.email}
            onChange={handleChange}
            required={!isLogin}
          />
          <input
            type="password"
            name="password"
            placeholder="密码"
            value={formData.password}
            onChange={handleChange}
            required
          />
          <button type="submit" className="btn btn-primary">
            {isLogin ? '登录' : '注册'}
          </button>
        </form>
        {message && <p className="message">{message}</p>}
        <p className="switch">
          {isLogin ? '没有账号？' : '已有账号？'}
          <button onClick={() => { setIsLogin(!isLogin); setMessage(''); }}>
            {isLogin ? '立即注册' : '立即登录'}
          </button>
        </p>
      </div>
    </div>
  );
}

export default App;
