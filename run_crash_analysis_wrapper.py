#!/usr/bin/env python3
"""
Crash Portfolio Analysis Wrapper

Runs the crash evaluation module from this folder.

Usage:
    python run_crash_analysis_wrapper.py

Or with custom config:
    python run_crash_analysis_wrapper.py --config config/enhanced_evaluation_config.json
"""

import sys
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        description='Run Crash Proof Quantum Portfolio Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_crash_analysis_wrapper.py                    # Use default data path
    python run_crash_analysis_wrapper.py --verbose          # Show detailed output
    python run_crash_analysis_wrapper.py --k 15             # Use 15 stocks instead of 10
        """
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/enhanced_evaluation_config.json',
        help='Path to crash-analysis config JSON'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed optimization output'
    )
    
    args = parser.parse_args()
    
    cfg_path = Path(args.config)
    if not cfg_path.exists():
        print(f"Error: Config file not found: {cfg_path}")
        sys.exit(1)
    
    print("="*80)
    print("CRASH PORTFOLIO ANALYSIS")
    print("="*80)
    print(f"Config: {cfg_path}")
    print(f"Verbose: {args.verbose}")
    print("="*80)
    print()
    
    import phase_08_crash_and_regime_evaluation as crash_phase
    
    print("Starting analysis...\n")

    crash_phase.main(config_path=str(cfg_path))
    
    print("\n" + "="*80)
    print("Analysis complete")
    print("="*80)
    print("\nCheck results folder for:")
    print("   • real_quantum_crash_analysis.png (visualization)")
    print("   • real_quantum_crash_results.json (detailed metrics)")
    print()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAnalysis interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
