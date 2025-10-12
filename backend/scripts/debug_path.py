import os, sys, argparse, glob

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    args = ap.parse_args()
    p = args.root
    print('RAW:', p)
    print('EXISTS:', os.path.exists(p))
    print('ISDIR:', os.path.isdir(p))
    if os.path.isdir(p):
        files = glob.glob(os.path.join(p, '**', '*.*'), recursive=True)
        print('COUNT:', len(files))
        for f in files[:10]:
            print('FILE:', f)

if __name__ == '__main__':
    main()
