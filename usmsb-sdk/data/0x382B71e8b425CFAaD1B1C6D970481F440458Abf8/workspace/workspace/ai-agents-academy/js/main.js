/**
 * AI Agents Academy - Main JavaScript
 * 处理网站交互逻辑
 */

document.addEventListener('DOMContentLoaded', function() {
    // 导航栏滚动效果
    const navbar = document.querySelector('.navbar');
    window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });

    // 数字滚动动画
    animateNumbers();
    
    // 课程卡片悬停效果
    initCourseCards();
    
    // 表单验证
    initForms();
    
    // 平滑滚动
    initSmoothScroll();
});

// 数字滚动动画
function animateNumbers() {
    const numbers = document.querySelectorAll('.stat-number');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const target = parseInt(entry.target.getAttribute('data-target'));
                animateValue(entry.target, 0, target, 2000);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });

    numbers.forEach(num => observer.observe(num));
}

function animateValue(element, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const value = Math.floor(progress * (end - start) + start);
        element.textContent = value.toLocaleString();
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

// 课程卡片交互
function initCourseCards() {
    const cards = document.querySelectorAll('.course-card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px)';
        });
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
}

// 表单验证
function initForms() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // 基本验证
            const name = form.querySelector('input[name="name"]');
            const email = form.querySelector('input[name="email"]');
            const phone = form.querySelector('input[name="phone"]');
            
            if (!name.value || !email.value || !phone.value) {
                alert('请填写所有必填项');
                return;
            }
            
            // 邮箱验证
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email.value)) {
                alert('请输入有效的邮箱地址');
                return;
            }
            
            // 显示成功提示
            alert('提交成功！我们的课程顾问将在24小时内与您联系。');
            form.reset();
        });
    });
}

// 平滑滚动
function initSmoothScroll() {
    const links = document.querySelectorAll('a[href^="#"]');
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// 移动端菜单切换
function toggleMenu() {
    const navLinks = document.querySelector('.nav-links');
    navLinks.classList.toggle('active');
}

// 模态框关闭
function closeModal() {
    const modal = document.querySelector('.modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// 点击模态框外部关闭
window.onclick = function(event) {
    const modal = document.querySelector('.modal');
    if (modal && event.target === modal) {
        modal.style.display = 'none';
    }
};
