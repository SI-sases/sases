import os
import tkinter as tk

flag = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "screenshots", "screen_click_ok.txt")
flag = os.path.abspath(flag)
os.makedirs(os.path.dirname(flag), exist_ok=True)
if os.path.exists(flag):
    os.remove(flag)

root = tk.Tk()
root.title("SASES Screen Test")
root.geometry("700x360+600+320")
root.attributes("-topmost", True)


def clicked():
    with open(flag, "w", encoding="utf-8") as handle:
        handle.write("clicked")
    label.config(text="CLICKED OK")
    root.after(500, root.destroy)


label = tk.Label(root, text="SASES SCREEN TEST", font=("Arial", 24))
label.pack(pady=30)
button = tk.Button(root, text="SASES_CLICK_TARGET", font=("Arial", 22), command=clicked)
button.pack(pady=20, ipadx=30, ipady=15)
root.after(45000, root.destroy)
root.mainloop()
