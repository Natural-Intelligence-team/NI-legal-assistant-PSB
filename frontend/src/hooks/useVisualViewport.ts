import { useEffect } from 'react';

export function useVisualViewport() {
  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return;

    const syncViewport = () => {
      document.documentElement.style.setProperty('--app-height', `${vv.height}px`);
      document.documentElement.style.setProperty('--app-offset-top', `${vv.offsetTop}px`);
    };

    syncViewport();
    vv.addEventListener('resize', syncViewport);
    vv.addEventListener('scroll', syncViewport);

    return () => {
      vv.removeEventListener('resize', syncViewport);
      vv.removeEventListener('scroll', syncViewport);
      document.documentElement.style.removeProperty('--app-height');
      document.documentElement.style.removeProperty('--app-offset-top');
    };
  }, []);
}
