"""Loopback-only local web interface."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import base64, binascii, io, json, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from PIL import Image, UnidentifiedImageError
from shared.engine import Recognizer

PAGE=Path(__file__).with_name('index.html')

class Handler(BaseHTTPRequestHandler):
    def reply(self,status,body,kind='application/json'):
        data=body.encode() if isinstance(body,str) else body
        self.send_response(status)
        self.send_header('Content-Type',kind+'; charset=utf-8')
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers();self.wfile.write(data)

    def do_GET(self):
        if self.path=='/':self.reply(200,PAGE.read_bytes(),'text/html')
        else:self.reply(404,'{"error":"Not found"}')

    def do_POST(self):
        if self.path!='/predict':return self.reply(404,'{"error":"Not found"}')
        origin=self.headers.get('Origin')
        if origin and origin!=f'http://127.0.0.1:{self.server.server_port}':
            return self.reply(403,'{"error":"Invalid origin"}')
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<500000:raise ValueError('Invalid request size.')
            data=json.loads(self.rfile.read(size))
            value=data['image']
            if not isinstance(value,str) or not value.startswith('data:image/png;base64,'):raise ValueError('Expected a PNG image.')
            raw=base64.b64decode(value.split(',',1)[1],validate=True)
            with Image.open(io.BytesIO(raw)) as image:
                if image.format!='PNG':raise ValueError('Expected a PNG image.')
                if image.width>1024 or image.height>1024:raise ValueError('Image is too large.')
                result=self.server.model.predict(image.convert('RGB'))
            self.reply(200,json.dumps(result))
        except (ValueError,KeyError,TypeError,UnidentifiedImageError,OSError,binascii.Error) as e:
            self.reply(400,json.dumps({'error':str(e)}))

if __name__=='__main__':
    model=Recognizer()
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    server.model=model
    url=f'http://127.0.0.1:{server.server_port}'
    print(f'Open {url}\nPress Ctrl+C to stop.',flush=True)
    threading.Timer(0.5,lambda:webbrowser.open(url)).start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
