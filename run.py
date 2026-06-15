#!/usr/bin/env python3
"""
Geofence Engine - Unified Orchestration Entry Point
==================================================
Provides a single interface to run extraction, merging, processing, 
testing, and visualization for the NITT geofence data.

Usage:
    python run.py --help
"""
import argparse
import subprocess
import sys
import os
import http.server
import socketserver
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def run_script(rel_path):
    script_path = os.path.join(BASE_DIR, rel_path)
    print(f"\n[run.py] Executing: {rel_path}...")
    result = subprocess.run([sys.executable, script_path], cwd=BASE_DIR)
    if result.returncode != 0:
        print(f"[run.py] ERROR: Script {rel_path} failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    print(f"[run.py] SUCCESS: {rel_path} completed.\n")

def cmd_pipeline(args):
    """Run the entire end-to-end data pipeline."""
    print("=" * 60)
    print("  RUNNING FULL GEOFENCE DATA PIPELINE")
    print("=" * 60)
    
    # 1. Extraction
    if args.osm or args.all:
        run_script("extraction/extract_v2.py")
    if args.msft or args.all:
        run_script("extraction/download_microsoft.py")
        
    # 2. Pipeline processing & merging
    if args.merge or args.all:
        run_script("pipeline/merge_pipeline.py")
    if args.export or args.all:
        run_script("pipeline/export_formats.py")
    if args.winding or args.all:
        run_script("pipeline/fix_winding.py")
        
    # 3. Validation
    if args.test or args.all:
        run_script("tests/test_raycasting.py")
        run_script("tests/usage.py")
        
    print("=" * 60)
    print("  PIPELINE EXECUTION COMPLETE")
    print("=" * 60)

def cmd_map(args):
    """Serve map.html using Python's built-in HTTP server."""
    port = args.port
    handler = http.server.SimpleHTTPRequestHandler
    
    # Serve from BASE_DIR to allow access to map/map.html and data/
    os.chdir(BASE_DIR)
    
    print("=" * 60)
    print(f"  Starting Map Visualization Server on port {port}")
    print(f"  Open in browser: http://localhost:{port}/map/map.html")
    print("  Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            # Open browser automatically
            webbrowser.open(f"http://localhost:{port}/map/map.html")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[run.py] Map server stopped.")
    except Exception as e:
        print(f"[run.py] ERROR: Failed to start server: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="NIT Trichy Geofence Engine - Orchestrator CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: pipeline
    pipe_parser = subparsers.add_parser("pipeline", help="Run data processing pipeline stages")
    pipe_group = pipe_parser.add_mutually_exclusive_group(required=True)
    pipe_group.add_argument("--all", action="store_true", help="Run all pipeline stages and tests")
    pipe_group.add_argument("--extract", dest="osm", action="store_true", help="Extract raw OSM university data")
    pipe_group.add_argument("--msft", action="store_true", help="Download MSFT Building Footprints quadkey tile")
    pipe_group.add_argument("--merge", action="store_true", help="Merge OSM, Microsoft, and Manual drawings")
    pipe_group.add_argument("--export", action="store_true", help="Export processed datasets to KML/GeoJSON")
    pipe_group.add_argument("--winding", action="store_true", help="Validate and correct GeoJSON winding orders")
    pipe_group.add_argument("--test", action="store_true", help="Run PiP raycasting and usage tests")
    pipe_parser.set_defaults(func=cmd_pipeline)

    # Subcommand: map
    map_parser = subparsers.add_parser("map", help="Serve map.html for visual exploration and editing")
    map_parser.add_argument("--port", type=int, default=8000, help="HTTP port to serve on (default: 8000)")
    map_parser.set_defaults(func=cmd_map)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
