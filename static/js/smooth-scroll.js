/**
 * Enhanced Smooth Scroll Implementation
 * A lightweight smooth scrolling implementation for the Information Retrieval System
 */
document.addEventListener('DOMContentLoaded', function() {
    // Smooth scroll initialization
    const smoothScroll = {
        init: function() {
            // Add smooth scrolling to all links
            document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                anchor.addEventListener('click', function(e) {
                    e.preventDefault();
                    
                    const targetId = this.getAttribute('href');
                    if (targetId === '#') return;
                    
                    const targetElement = document.querySelector(targetId);
                    if (targetElement) {
                        window.scrollTo({
                            top: targetElement.offsetTop - 100,
                            behavior: 'smooth'
                        });
                    }
                });
            });
            
            // Add scroll animations
            this.addScrollAnimations();
            
            // Add scroll progress indicator
            this.addScrollProgress();
        },
        
        addScrollAnimations: function() {
            const animatedElements = document.querySelectorAll('.animate-on-scroll');
            
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('visible');
                        
                        // Add staggered animations for child elements if they exist
                        const animatedChildren = entry.target.querySelectorAll('.stagger-animation');
                        if (animatedChildren.length > 0) {
                            animatedChildren.forEach((child, index) => {
                                setTimeout(() => {
                                    child.classList.add('visible');
                                }, 100 * index);
                            });
                        }
                    }
                });
            }, {
                threshold: 0.1,
                rootMargin: '0px 0px -50px 0px'
            });
            
            animatedElements.forEach(element => {
                observer.observe(element);
            });
        },
        
        addScrollProgress: function() {
            const progressBar = document.querySelector('.scroll-progress');
            if (!progressBar) return;
            
            window.addEventListener('scroll', () => {
                const scrollTop = document.documentElement.scrollTop || document.body.scrollTop;
                const scrollHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
                const scrollPercentage = (scrollTop / scrollHeight) * 100;
                
                progressBar.style.width = scrollPercentage + '%';
            });
        }
    };
    
    // Initialize smooth scroll
    smoothScroll.init();
    
    // Add hover animations for interactive elements
    const addHoverEffects = () => {
        const interactiveElements = document.querySelectorAll('.search-button, .advanced-search-link, .footer-social a');
        
        interactiveElements.forEach(element => {
            element.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-2px)';
                this.style.transition = 'transform 0.3s ease';
            });
            
            element.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
            });
        });
    };
    
    addHoverEffects();
});
