"""Tkinter desktop digit recognition."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageDraw, ImageTk
from shared.engine import Recognizer

class App:
    def __init__(self,root):
        self.model=Recognizer()
        self.root=root
        root.title('Digit Studio | MNIST')
        root.configure(bg='#f1f5f9')
        root.resizable(False,False)
        wrap=ttk.Frame(root,padding=24)
        wrap.pack()
        ttk.Label(wrap,text='Digit Studio',font=('Segoe UI',24,'bold')).pack(anchor='w')
        ttk.Label(wrap,text='Draw one digit from 0 to 9.',padding=(0,8)).pack(anchor='w')
        self.canvas=tk.Canvas(wrap,width=336,height=336,bg='white',highlightthickness=1,highlightbackground='#cbd5e1')
        self.canvas.pack(pady=8)
        self.canvas.bind('<ButtonPress-1>',self.start)
        self.canvas.bind('<B1-Motion>',self.move)
        self.canvas.bind('<ButtonRelease-1>',lambda e:setattr(self,'last',None))
        row=ttk.Frame(wrap);row.pack(fill='x',pady=10)
        ttk.Button(row,text='Clear',command=self.clear).pack(side='left')
        ttk.Button(row,text='Recognize',command=self.recognize).pack(side='right')
        self.result=ttk.Label(wrap,text='',font=('Segoe UI',18,'bold'));self.result.pack()
        self.details=ttk.Label(wrap,text='');self.details.pack(pady=8)
        ttk.Label(wrap,text='Model confidence is not a guarantee of correctness.').pack()
        root.bind('<Return>',lambda e:self.recognize())
        root.bind('<Escape>',lambda e:self.clear())
        self.clear()

    def clear(self):
        self.canvas.delete('all')
        self.image=Image.new('RGB',(336,336),'white')
        self.draw=ImageDraw.Draw(self.image)
        self.last=None
        self.result.config(text='Ready to draw')
        self.details.config(text='Enter: recognize | Esc: clear')

    def start(self,event):
        self.last=(event.x,event.y)
        self.stroke(self.last,self.last)

    def move(self,event):
        point=(max(0,min(335,event.x)),max(0,min(335,event.y)))
        if self.last:self.stroke(self.last,point)
        self.last=point

    def stroke(self,a,b):
        self.canvas.create_line(*a,*b,fill='#111111',width=22,capstyle=tk.ROUND)
        self.draw.line([a,b],fill='#111111',width=22)
        for x,y in (a,b):
            self.canvas.create_oval(x-11,y-11,x+11,y+11,fill='#111111',outline='')
            self.draw.ellipse((x-11,y-11,x+11,y+11),fill='#111111')
        self.result.config(text='Ready to recognize')
        self.details.config(text='')

    def recognize(self):
        try:
            r=self.model.predict(self.image)
            self.result.config(text=f"{r['digit']}  |  {r['confidence']:.1%} confidence")
            top=sorted(enumerate(r['probabilities']),key=lambda x:-x[1])[:3]
            self.details.config(text='Top 3: '+ '   '.join(f'{d}: {p:.1%}' for d,p in top))
        except ValueError as e:messagebox.showinfo('Draw a digit',str(e))

if __name__=='__main__':
    root=tk.Tk()
    try:App(root)
    except Exception as e:
        messagebox.showerror('Startup error',str(e));root.destroy();sys.exit(1)
    root.mainloop()
