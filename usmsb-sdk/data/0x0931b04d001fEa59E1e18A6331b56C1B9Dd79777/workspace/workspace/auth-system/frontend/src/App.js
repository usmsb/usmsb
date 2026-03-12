import React, { useState } from 'react';

const API_URL = 'http://localhost:3001/api';

function App() {
  const [isLogin, setIsLogin] = useState(true);
  const [user, setUser] = useState(null);
  const [message, setMessage] = useState('');
  
  // Form states
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');

  const handleRegister = async (e) => {
    e.preventDefault();
    setMessage('');
    
    try {
      const response = await fetch(`${API_URL}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, email })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setMessage('注册成功！请登录');
        setIsLogin(true);
        setUsername('');
        setPassword('');
        setEmail('');
      } else {
        setMessage(data.message);
      }
    } catch (error) {
      setMessage('注册失败: ' + error.message);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setMessage('');
    
    try {
      const response = await fetch(`${API_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setUser(data.user);
        setMessage('');
      } else {
        setMessage(data.message);
      }
    } catch (error) {
      setMessage('登录失败: ' + error.message);
    }
  };

  const handleLogout = () => {
    setUser(null);
    setUsername('');
    setPassword('');
    setEmail('');
    setMessage('');
  };

  // Show user info after login
  if (user) {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <h2>🎉 登录成功！</h2>
          <div style={styles.userInfo}>
            <p><strong>用户ID:</strong> {user.id}</p>
            <p><strong>用户名:</strong> {user.username}</p>
            <p><strong>邮箱:</strong> {user.email}</p>
          </div>
          <button style={styles.button} onClick={handleLogout}>退出登录</button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>
          {isLogin ? '用户登录' : '用户注册'}
        </h1>
        
        <form onSubmit={isLogin ? handleLogin : handleRegister}>
          <input
            type="text"
            placeholder="用户名"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={styles.input}
            required
          />
          
          {!isLogin && (
            <input
              type="email"
              placeholder="邮箱"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={styles.input}
              required
            />
          )}
          
          <input
            type="password"
            placeholder="密码"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={styles.input}
            required
          />
          
          <button type="submit" style={styles.button}>
            {isLogin ? '登录' : '注册'}
          </button>
        </form>
        
        {message && (
          <p style={message.includes('成功') ? styles.success : styles.error}>
            {message}
          </p>
        )}
        
        <p style={styles.switch}>
          {isLogin ? '还没有账号？' : '已有账号？'}
          <button 
            style={styles.linkButton}
            onClick={() => {
              setIsLogin(!isLogin);
              setMessage('');
            }}
          >
            {isLogin ? '立即注册' : '立即登录'}
          </button>
        </p>
      </div>
    </div>
  );
}

const styles = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f5f5f5',
    fontFamily: 'Arial, sans-serif'
  },
  card: {
    backgroundColor: 'white',
    padding: '40px',
    borderRadius: '10px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
    width: '100%',
    maxWidth: '400px'
  },
  title: {
    textAlign: 'center',
    marginBottom: '30px',
    color: '#333'
  },
  input: {
    width: '100%',
    padding: '12px',
    marginBottom: '15px',
    border: '1px solid #ddd',
    borderRadius: '5px',
    fontSize: '14px',
    boxSizing: 'border-box'
  },
  button: {
    width: '100%',
    padding: '12px',
    backgroundColor: '#007bff',
    color: 'white',
    border: 'none',
    borderRadius: '5px',
    fontSize: '16px',
    cursor: 'pointer',
    marginTop: '10px'
  },
  switch: {
    textAlign: 'center',
    marginTop: '20px',
    color: '#666'
  },
  linkButton: {
    background: 'none',
    border: 'none',
    color: '#007bff',
    cursor: 'pointer',
    fontSize: '14px',
    textDecoration: 'underline'
  },
  success: {
    color: '#28a745',
    textAlign: 'center',
    marginTop: '15px'
  },
  error: {
    color: '#dc3545',
    textAlign: 'center',
    marginTop: '15px'
  },
  userInfo: {
    backgroundColor: '#f8f9fa',
    padding: '15px',
    borderRadius: '5px',
    marginBottom: '20px'
  }
};

export default App;
