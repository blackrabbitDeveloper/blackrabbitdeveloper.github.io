(function () {
  'use strict';

  // ── Theme toggle ──
  function getPreferredTheme() {
    var stored = localStorage.getItem('theme');
    if (stored) return stored;
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    var metaTheme = document.querySelector('meta[name="theme-color"]');
    if (metaTheme) {
      metaTheme.setAttribute('content', theme === 'light' ? '#fafafa' : '#0a0a0a');
    }
  }

  function toggleTheme() {
    var current = document.documentElement.getAttribute('data-theme') || 'dark';
    var next = current === 'dark' ? 'light' : 'dark';
    localStorage.setItem('theme', next);
    applyTheme(next);
  }

  // Apply theme on load (backup for FOUC script)
  applyTheme(getPreferredTheme());

  // Bind toggle buttons
  document.querySelectorAll('.theme-toggle').forEach(function (btn) {
    btn.addEventListener('click', toggleTheme);
  });

  // ── Smooth scroll for in-page anchor links ──
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    var id = anchor.getAttribute('href');
    if (id === '#') return;
    var target = document.querySelector(id);
    if (!target) return;
    anchor.addEventListener('click', function (e) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });

  // ── Mobile hamburger menu toggle ──
  var menuToggle = document.getElementById('menu-toggle');
  var mobileMenu = document.getElementById('mobile-menu');
  var iconOpen   = document.getElementById('icon-open');
  var iconClose  = document.getElementById('icon-close');

  if (menuToggle && mobileMenu) {
    menuToggle.addEventListener('click', function () {
      var isOpen = !mobileMenu.classList.contains('hidden');
      mobileMenu.classList.toggle('hidden', isOpen);
      iconOpen.classList.toggle('hidden', !isOpen);
      iconClose.classList.toggle('hidden', isOpen);
      menuToggle.setAttribute('aria-expanded', String(!isOpen));
      menuToggle.setAttribute('aria-label', isOpen ? '메뉴 열기' : '메뉴 닫기');
    });

    mobileMenu.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        mobileMenu.classList.add('hidden');
        iconOpen.classList.remove('hidden');
        iconClose.classList.add('hidden');
        menuToggle.setAttribute('aria-expanded', 'false');
        menuToggle.setAttribute('aria-label', '메뉴 열기');
      });
    });
  }

  // ── TOC (Table of Contents) ──
  var tocContainer = document.getElementById('toc');
  var prose = document.querySelector('.prose');

  if (tocContainer && prose) {
    var headings = prose.querySelectorAll('h2, h3');

    if (headings.length >= 2) {
      // Assign IDs and build list
      var list = tocContainer.querySelector('.toc-list');
      headings.forEach(function (heading, i) {
        if (!heading.id) {
          heading.id = 'heading-' + i;
        }
        var li = document.createElement('li');
        var a = document.createElement('a');
        a.href = '#' + heading.id;
        a.textContent = heading.textContent;
        if (heading.tagName === 'H3') a.classList.add('toc-h3');
        a.addEventListener('click', function (e) {
          e.preventDefault();
          heading.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
        li.appendChild(a);
        list.appendChild(li);
      });

      // Toggle collapse
      var header = tocContainer.querySelector('.toc-header');
      header.addEventListener('click', function () {
        tocContainer.classList.toggle('collapsed');
      });

      // Intersection Observer for active highlight
      var tocLinks = list.querySelectorAll('a');
      var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            tocLinks.forEach(function (l) { l.classList.remove('active'); });
            var activeLink = list.querySelector('a[href="#' + entry.target.id + '"]');
            if (activeLink) activeLink.classList.add('active');
          }
        });
      }, { rootMargin: '0px 0px -70% 0px', threshold: 0 });

      headings.forEach(function (h) { observer.observe(h); });
    } else {
      tocContainer.style.display = 'none';
    }
  }

  // ── Share buttons ──
  var shareTwitter = document.getElementById('share-twitter');
  var shareFacebook = document.getElementById('share-facebook');
  var shareCopy = document.getElementById('share-copy');

  if (shareTwitter) {
    shareTwitter.addEventListener('click', function (e) {
      e.preventDefault();
      var url = encodeURIComponent(window.location.href);
      var title = encodeURIComponent(document.title);
      window.open('https://twitter.com/intent/tweet?url=' + url + '&text=' + title, '_blank', 'width=550,height=420');
    });
  }

  if (shareFacebook) {
    shareFacebook.addEventListener('click', function (e) {
      e.preventDefault();
      var url = encodeURIComponent(window.location.href);
      window.open('https://www.facebook.com/sharer/sharer.php?u=' + url, '_blank', 'width=550,height=420');
    });
  }

  if (shareCopy) {
    shareCopy.addEventListener('click', function () {
      navigator.clipboard.writeText(window.location.href).then(function () {
        shareCopy.classList.add('share-copied');
        setTimeout(function () {
          shareCopy.classList.remove('share-copied');
        }, 2000);
      });
    });
  }

  // ── Glossary search ──
  var glossaryInput = document.getElementById('glossary-search');
  if (glossaryInput) {
    glossaryInput.addEventListener('input', function () {
      var query = this.value.toLowerCase();
      document.querySelectorAll('.glossary-item').forEach(function (item) {
        var text = item.textContent.toLowerCase();
        item.style.display = text.includes(query) ? '' : 'none';
      });
    });
  }

  // ── Scroll progress bar (post pages only) ──
  var progressBar = document.getElementById('scroll-progress');
  var articleEl = document.querySelector('article');

  if (progressBar && articleEl) {
    var ticking = false;
    window.addEventListener('scroll', function () {
      if (!ticking) {
        requestAnimationFrame(function () {
          var scrollTop = window.scrollY;
          var docHeight = articleEl.offsetHeight - window.innerHeight;
          if (docHeight > 0) {
            var progress = Math.min((scrollTop / docHeight) * 100, 100);
            progressBar.style.width = progress + '%';
          }
          ticking = false;
        });
        ticking = true;
      }
    });
  }

  // ── Fade-in on scroll ──
  var fadeEls = document.querySelectorAll('.fade-in-up');
  if (fadeEls.length > 0 && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    var fadeObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          fadeObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });

    fadeEls.forEach(function (el) { fadeObserver.observe(el); });
  } else {
    // If reduced motion, make all visible immediately
    fadeEls.forEach(function (el) { el.classList.add('visible'); });
  }

})();
