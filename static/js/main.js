/* Probob Design Studio — Enhanced JS */

document.addEventListener('DOMContentLoaded', () => {

  // ── Navbar scroll effect ─────────────────────────────
  const navbar = document.getElementById('navbar');
  window.addEventListener('scroll', () => {
    if (window.scrollY > 40) {
      navbar?.classList.add('scrolled');
    } else {
      navbar?.classList.remove('scrolled');
    }
  }, { passive: true });

  // ── Mobile menu ──────────────────────────────────────
  const hamburger = document.getElementById('hamburger');
  const mobileMenu = document.getElementById('mobileMenu');
  hamburger?.addEventListener('click', () => {
    const open = mobileMenu.classList.toggle('open');
    document.body.style.overflow = open ? 'hidden' : '';
    // Animate hamburger to X
    const spans = hamburger.querySelectorAll('span');
    if (open) {
      spans[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
      spans[1].style.opacity = '0';
      spans[2].style.transform = 'rotate(-45deg) translate(5px, -5px)';
    } else {
      spans.forEach(s => { s.style.transform = ''; s.style.opacity = ''; });
    }
  });

  // ── FAQ accordion ────────────────────────────────────
  document.querySelectorAll('.faq-question').forEach(btn => {
    btn.addEventListener('click', () => {
      const item = btn.closest('.faq-item');
      const isOpen = item.classList.contains('open');
      document.querySelectorAll('.faq-item.open').forEach(el => el.classList.remove('open'));
      if (!isOpen) item.classList.add('open');
    });
  });

  // ── Careers: click job → fill apply form ────────────
  document.querySelectorAll('.apply-trigger').forEach(btn => {
    btn.addEventListener('click', () => {
      const title = btn.dataset.title;
      const input = document.getElementById('jobTitleInput');
      if (input) {
        input.value = title;
        document.getElementById('applyPanel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // ── Auto-dismiss flash messages ──────────────────────
  document.querySelectorAll('.flash').forEach(flash => {
    setTimeout(() => {
      flash.style.opacity = '0';
      flash.style.transform = 'translateX(20px)';
      flash.style.transition = 'opacity .4s, transform .4s';
      setTimeout(() => flash.remove(), 400);
    }, 5000);
  });

  // ── Scroll-reveal animation ──────────────────────────
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('revealed');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

  const revealTargets = [
    '.work-card', '.service-tile', '.testimonial-card',
    '.portfolio-card', '.blog-card', '.price-card',
    '.service-detail-card', '.team-card', '.case-card',
    '.stat-item', '.process-step', '.job-card'
  ];

  revealTargets.forEach(sel => {
    document.querySelectorAll(sel).forEach((el, i) => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(24px)';
      el.style.transition = `opacity .5s ease ${i * 0.08}s, transform .5s ease ${i * 0.08}s`;
      observer.observe(el);
    });
  });

  // Add revealed style
  const style = document.createElement('style');
  style.textContent = '.revealed { opacity: 1 !important; transform: translateY(0) !important; }';
  document.head.appendChild(style);

  // ── Dropdown accessibility: close on outside click ───
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.nav-dropdown')) {
      document.querySelectorAll('.dropdown-menu').forEach(m => m.style.display = '');
    }
  });

  // ── Smooth counter animation for stats ───────────────
  const countEls = document.querySelectorAll('.stat-num');
  const counterObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el = entry.target;
        const plusEl = el.querySelector('.stat-plus');
        const rawText = el.textContent.replace('+','').trim();
        const target = parseInt(rawText, 10);
        if (isNaN(target)) return;
        let current = 0;
        const duration = 1200;
        const step = (timestamp) => {
          if (!start) start = timestamp;
          const progress = Math.min((timestamp - start) / duration, 1);
          const eased = 1 - Math.pow(1 - progress, 3);
          current = Math.floor(eased * target);
          el.childNodes[0].textContent = current;
          if (plusEl) el.appendChild(plusEl);
          if (progress < 1) requestAnimationFrame(step);
        };
        let start;
        requestAnimationFrame(step);
        counterObserver.unobserve(el);
      }
    });
  }, { threshold: 0.5 });

  countEls.forEach(el => counterObserver.observe(el));

});
