#!/usr/bin/env python3
"""
Simple HTTP server to serve Mintlify documentation files
Since Mintlify CLI has environment issues, this serves the raw MDX files with basic HTML wrapper
"""
import http.server
import socketserver
import os
import json
import sys
from pathlib import Path
from urllib.parse import unquote

class DocsHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="/home/amorelli/development/sec-edgar-mcp/docs", **kwargs)
    
    def do_GET(self):
        # Parse the requested path
        path = unquote(self.path.lstrip('/'))
        if not path:
            path = 'introduction'
        
        # Remove .html extension if present
        if path.endswith('.html'):
            path = path[:-5]
        
        # Try to serve the corresponding .mdx file
        mdx_file = Path(self.directory) / f"{path}.mdx"
        
        if mdx_file.exists():
            self.serve_mdx_as_html(mdx_file, path)
        elif path == 'mint.json':
            super().do_GET()
        else:
            # Try to serve as regular file
            super().do_GET()
    
    def serve_mdx_as_html(self, mdx_file, page_name):
        """Convert MDX to basic HTML and serve"""
        try:
            with open(mdx_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract frontmatter
            title = page_name.replace('-', ' ').replace('/', ' - ').title()
            description = ""
            
            if content.startswith('---\n'):
                end_idx = content.find('\n---\n', 4)
                if end_idx > 0:
                    frontmatter = content[4:end_idx]
                    content = content[end_idx + 5:]
                    
                    for line in frontmatter.split('\n'):
                        if line.startswith('title:'):
                            title = line.split('title:')[1].strip().strip('"\'')
                        elif line.startswith('description:'):
                            description = line.split('description:')[1].strip().strip('"\'')
            
            # Load navigation from mint.json
            nav_html = self.generate_navigation()
            
            # Basic HTML wrapper
            html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - SEC Edgar MCP Documentation</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            line-height: 1.6; 
            color: #333;
            background: #fafafa;
        }}
        .container {{ 
            display: flex; 
            min-height: 100vh; 
        }}
        .sidebar {{ 
            width: 300px; 
            background: white; 
            border-right: 1px solid #e5e5e5; 
            padding: 20px; 
            overflow-y: auto;
        }}
        .main {{ 
            flex: 1; 
            padding: 40px; 
            background: white; 
            margin: 20px; 
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .nav-group {{ margin-bottom: 20px; }}
        .nav-group-title {{ 
            font-weight: 600; 
            color: #2563EB; 
            margin-bottom: 8px; 
            font-size: 14px; 
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .nav-link {{ 
            display: block; 
            padding: 6px 12px; 
            color: #666; 
            text-decoration: none; 
            border-radius: 4px; 
            font-size: 14px;
            margin-bottom: 2px;
        }}
        .nav-link:hover {{ background: #f3f4f6; color: #2563EB; }}
        .nav-link.active {{ background: #2563EB; color: white; }}
        h1, h2, h3, h4, h5, h6 {{ margin: 20px 0 10px 0; color: #1f2937; }}
        h1 {{ font-size: 2.5rem; border-bottom: 2px solid #2563EB; padding-bottom: 10px; }}
        h2 {{ font-size: 2rem; margin-top: 30px; }}
        p {{ margin-bottom: 15px; }}
        pre {{ 
            background: #f8f9fa; 
            border: 1px solid #e9ecef; 
            border-radius: 4px; 
            padding: 15px; 
            overflow-x: auto; 
            margin: 15px 0;
        }}
        code {{ 
            background: #f1f5f9; 
            padding: 2px 4px; 
            border-radius: 3px; 
            font-size: 0.9em;
        }}
        pre code {{ background: none; padding: 0; }}
        .warning, .tip, .info {{ 
            padding: 15px; 
            margin: 15px 0; 
            border-radius: 4px; 
            border-left: 4px solid;
        }}
        .warning {{ background: #fef3cd; border-color: #f59e0b; }}
        .tip {{ background: #d1fae5; border-color: #10b981; }}
        .info {{ background: #dbeafe; border-color: #3b82f6; }}
        .header {{ 
            background: #2563EB; 
            color: white; 
            padding: 15px 20px; 
            font-size: 18px; 
            font-weight: 600;
        }}
        ul, ol {{ margin: 10px 0 10px 20px; }}
        li {{ margin-bottom: 5px; }}
        a {{ color: #2563EB; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <div class="header">SEC Edgar MCP</div>
            {nav_html}
        </div>
        <div class="main">
            {self.convert_markdown_to_html(content)}
        </div>
    </div>
</body>
</html>"""
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error serving file: {str(e)}")
    
    def generate_navigation(self):
        """Generate navigation HTML from mint.json"""
        try:
            with open(Path(self.directory) / 'mint.json', 'r') as f:
                config = json.load(f)
            
            nav_html = ""
            for group in config.get('navigation', []):
                nav_html += f'<div class="nav-group">'
                nav_html += f'<div class="nav-group-title">{group["group"]}</div>'
                
                for page in group.get('pages', []):
                    page_url = page.replace('/', '--')  # Convert slashes for URL
                    nav_html += f'<a href="/{page}" class="nav-link">{page.replace("-", " ").replace("/", " / ").title()}</a>'
                
                nav_html += '</div>'
                
            return nav_html
        except:
            return '<div class="nav-group"><div class="nav-group-title">Documentation</div></div>'
    
    def convert_markdown_to_html(self, content):
        """Basic markdown to HTML conversion"""
        lines = content.split('\n')
        html_lines = []
        in_code_block = False
        code_lang = ""
        
        for line in lines:
            # Code blocks
            if line.startswith('```'):
                if in_code_block:
                    html_lines.append('</code></pre>')
                    in_code_block = False
                else:
                    code_lang = line[3:].strip()
                    html_lines.append(f'<pre><code>')
                    in_code_block = True
                continue
            
            if in_code_block:
                html_lines.append(line.replace('<', '&lt;').replace('>', '&gt;'))
                continue
            
            # Headers
            if line.startswith('# '):
                html_lines.append(f'<h1>{line[2:]}</h1>')
            elif line.startswith('## '):
                html_lines.append(f'<h2>{line[3:]}</h2>')
            elif line.startswith('### '):
                html_lines.append(f'<h3>{line[4:]}</h3>')
            elif line.startswith('#### '):
                html_lines.append(f'<h4>{line[5:]}</h4>')
            # Special blocks
            elif line.strip().startswith('<Warning>') or line.strip().startswith('<Tip>') or line.strip().startswith('<Info>'):
                block_type = 'warning' if 'Warning' in line else ('tip' if 'Tip' in line else 'info')
                html_lines.append(f'<div class="{block_type}">')
            elif line.strip() in ['</Warning>', '</Tip>', '</Info>']:
                html_lines.append('</div>')
            # Lists
            elif line.strip().startswith('- '):
                if not html_lines or not html_lines[-1].startswith('<li>'):
                    if html_lines and html_lines[-1] != '</ul>':
                        html_lines.append('<ul>')
                html_lines.append(f'<li>{line.strip()[2:]}</li>')
            # Paragraphs
            elif line.strip():
                if html_lines and html_lines[-1].startswith('<li>'):
                    html_lines.append('</ul>')
                html_lines.append(f'<p>{line}</p>')
            else:
                if html_lines and html_lines[-1].startswith('<li>'):
                    html_lines.append('</ul>')
                html_lines.append('<br>')
        
        # Close any open lists
        if html_lines and html_lines[-1].startswith('<li>'):
            html_lines.append('</ul>')
            
        return '\n'.join(html_lines)

if __name__ == "__main__":
    PORT = 3015
    
    try:
        with socketserver.TCPServer(("", PORT), DocsHandler) as httpd:
            print(f"🚀 SEC Edgar MCP Documentation Server")
            print(f"📚 Serving at: http://localhost:{PORT}")
            print(f"📝 Documentation: http://localhost:{PORT}/introduction")
            print(f"⚡ Quick start: http://localhost:{PORT}/quickstart")
            print(f"🛠️  Tools: http://localhost:{PORT}/tools/overview")
            print(f"")
            print(f"Note: This is a simple HTML server serving the Mintlify")
            print(f"documentation files due to environment issues with the")
            print(f"official Mintlify CLI. All content is preserved.")
            print(f"")
            print("Press Ctrl+C to stop the server")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"\n👋 Server stopped")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {PORT} is already in use. Try a different port.")
        else:
            print(f"❌ Error starting server: {e}")
        sys.exit(1)