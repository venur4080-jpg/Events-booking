(function() {
    const scripts = document.getElementsByTagName('script');
    const currentScript = scripts[scripts.length - 1];
    const eventId = currentScript.getAttribute('data-event-id') || '1';
    const baseUrl = currentScript.src.replace(/\/static\/widget\.js.*$/, '');

    const iframe = document.createElement('iframe');
    iframe.src = `${baseUrl}/embed/event/${eventId}`;
    iframe.style.border = 'none';
    iframe.style.width = '380px';
    iframe.style.height = '230px';
    iframe.style.borderRadius = '18px';
    iframe.style.overflow = 'hidden';
    iframe.style.boxShadow = '0 10px 30px rgba(0,0,0,0.4)';

    currentScript.parentNode.insertBefore(iframe, currentScript);
})();
