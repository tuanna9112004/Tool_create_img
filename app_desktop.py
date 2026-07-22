import os
import webview

def run_desktop_app():
    # Path to index.html
    html_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "index.html"))
    
    # Create window
    window = webview.create_window(
        title="Whisk Image Generator Pro by creatornow.com.vn",
        url=f"file:///{html_file}",
        width=1400,
        height=900,
        resizable=True,
        min_size=(1000, 700)
    )
    
    webview.start()

if __name__ == "__main__":
    run_desktop_app()
