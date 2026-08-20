@echo off
REM Install pip dependencies that aren't available on conda-forge
echo Installing additional dependencies via pip...
"%PREFIX%\Scripts\pip.exe" install "mcp[cli]>=1.7.1,<2" "sec-edgar-toolkit[pandas]>=0.2.0" --quiet
echo SEC EDGAR MCP installation complete!