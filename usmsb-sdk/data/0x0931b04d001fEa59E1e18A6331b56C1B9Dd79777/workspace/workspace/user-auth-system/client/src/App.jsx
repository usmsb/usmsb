import { useState } from 'react'

function App() {
  const [activeTab, setActiveTab] = useState('login')
  const [message, setMessage] = useState({ type: '', text: '' })
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [user, setUser] = useState(null)
  
  const [loginData, setLoginData] = useState({ username: '', password: '' })
  const [registerData, setRegisterData] = useState({ username: '', email: '', password: '', confirmPassword: '' })

  const handleLogin = async (e) => {
    e.preventDefault()
    setMessage({ type: '', text: '' })
    
    try {
      const response = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loginData)
      })
      
      const data = await response.json()
      
      if (data.success) {
        setUser(data.user)
        setIsLoggedIn(true)
        setMessage({ type: 'success', text: data.message })
      } else {
        setMessage({ type: 'error', text: data.message })
      }
    } catch (error) {
      setMessage({ type: 'error', text: '网络错误，请稍后重试' })
    }
  }

  const handleRegister = async (e) => {
    e.preventDefault()
    setMessage({ type: '', text: '' })
    
    if (registerData.password !== registerData.confirmPassword) {
      setMessage({ type: 'error', text: '两次输入的密码不一致' })
      return
    }
    
    if (registerData.password.length < 6) {
      setMessage({ type: 'error', text: '密码长度至少为6位' })
      return
    }
    
    try {
      const response = await fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: registerData.username,
          email: registerData.email,
          password: registerData.password
        })
      })
      
      const data = await response.json()
      
      if (data.success) {
        setMessage({ type: 'success', text: '注册成功！请登录' })
        setActiveTab('login')
        setLoginData({ username: registerData.username, password: '' })
        setRegisterData({ username: '', email: '', password: '', confirmPassword: '' })
      } else {
        setMessage({ type: 'error', text: data.message })
      }
    } catch (error) {
      setMessage({ type: 'error', text: '网络错误，请稍后重试' })
    }
  }

  const handleLogout = () => {
    setUser(null)
    setIsLoggedIn(false)
    setLoginData({ username: '', password: '' })
    setMessage({ type: '', text: '' })
  }

  if (isLoggedIn && user) {
    return (
      <div className="container">
        <div className="form-container user-info">
          <h1>🎉 登录成功</h1>
          <p>欢迎回来</p>
          <div className="username">{user.username}</div>
          <p>邮箱: {user.email}</p>
          <p>用户ID: {user.id}</p>
          <button className="btn btn-secondary" onClick={handleLogout} style={{ marginTop: '20px' }}>
            退出登录
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="container">
      <div className="tabs">
        <button 
          className={`tab ${activeTab === 'login' ? 'active' : ''}`}
          onClick={() => { setActiveTab('login'); setMessage({ type: '', text: '' }) }}
        >
          登录
        </button>
        <button 
          className={`tab ${activeTab === 'register' ? 'active' : ''}`}
          onClick={() => { setActiveTab('register'); setMessage({ type: '', text: '' }) }}
        >
          注册
        </button>
      </div>
      
      <div className="form-container">
        {message.text && (
          <div className={`message ${message.type}`}>
            {message.text}
          </div>
        )}
        
        {activeTab === 'login' ? (
          <form onSubmit={handleLogin}>
            <h1>用户登录</h1>
            <div className="form-group">
              <label>用户名</label>
              <input
                type="text"
                value={loginData.username}
                onChange={(e) => setLoginData({ ...loginData, username: e.target.value })}
                placeholder="请输入用户名"
                required
              />
            </div>
            <div className="form-group">
              <label>密码</label>
              <input
                type="password"
                value={loginData.password}
                onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                placeholder="请输入密码"
                required
              />
            </div>
            <button type="submit" className="btn btn-primary">
              登录
            </button>
          </form>
        ) : (
          <form onSubmit={handleRegister}>
            <h1>用户注册</h1>
            <div className="form-group">
              <label>用户名</label>
              <input
                type="text"
                value={registerData.username}
                onChange={(e) => setRegisterData({ ...registerData, username: e.target.value })}
                placeholder="请输入用户名"
                required
              />
            </div>
            <div className="form-group">
              <label>邮箱</label>
              <input
                type="email"
                value={registerData.email}
                onChange={(e) => setRegisterData({ ...registerData, email: e.target.value })}
                placeholder="请输入邮箱"
                required
              />
            </div>
            <div className="form-group">
              <label>密码</label>
              <input
                type="password"
                value={registerData.password}
                onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })}
                placeholder="请输入密码（至少6位）"
                required
              />
            </div>
            <div className="form-group">
              <label>确认密码</label>
              <input
                type="password"
                value={registerData.confirmPassword}
                onChange={(e) => setRegisterData({ ...registerData, confirmPassword: e.target.value })}
                placeholder="请再次输入密码"
                required
              />
            </div>
            <button type="submit" className="btn btn-primary">
              注册
            </button>
          </form>
        )}
      </div>
    </div>
  )
}

export default App
