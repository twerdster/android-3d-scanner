"""Run from repository root: python3 -m updated.cli simulate."""
import argparse
from pathlib import Path
from .report import generate_report

def main():
    parser=argparse.ArgumentParser(description='Beam synthetic structured-light replay')
    sub=parser.add_subparsers(dest='command',required=True)
    simulate=sub.add_parser('simulate')
    simulate.add_argument('--output',type=Path,default=Path('updated/results'))
    simulate.add_argument('--android-asset',type=Path)
    args=parser.parse_args()
    data=generate_report(args.output,args.android_asset)
    print(f"Generated {len(data['scenes'])} geometric scenarios: {args.output}/index.html")

if __name__=='__main__':main()
