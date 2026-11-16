"""Local QR rendering. Caller supplies only a whitelisted current remote URL."""
from functools import lru_cache
from html import escape
from public.support.vendor.qrcodegen import QrCode


@lru_cache(maxsize=16)
def qr_svg(url):
    qr = QrCode.encode_text(url, QrCode.Ecc.MEDIUM)
    size = qr.get_size()
    # Four-module quiet zone and opaque white background are necessary for scans.
    path = ' '.join(f'M{x+4},{y+4}h1v1h-1z' for y in range(size) for x in range(size) if qr.get_module(x, y))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size+8} {size+8}" role="img" aria-label="Fernbedienung öffnen" shape-rendering="crispEdges">'
            f'<title>{escape(url)}</title><rect width="100%" height="100%" fill="#fff"/>'
            f'<path d="{path}" fill="#000"/></svg>').encode('utf-8')
