"""Command line: crystallyzer serve | diffract | polarize | grow | check."""

from __future__ import annotations

import argparse
import sys

from . import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="crystallyzer", description="A Raspberry Pi optical bench for crystals.")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("serve", help="Run the touchscreen app")
    s.add_argument("--simulate", action="store_true", help="Use the physics simulator instead of hardware")
    s.add_argument("--host", default="0.0.0.0")
    s.add_argument("--port", type=int, default=8080)

    d = sub.add_parser("diffract", help="Capture and read one diffraction pattern")
    d.add_argument("--simulate", metavar="SLIDE", help="Simulate this slide instead of using the laser")

    p = sub.add_parser("polarize", help="Turn a crystal between crossed polarizers")
    p.add_argument("--simulate", metavar="CRYSTAL", help="Simulate this crystal instead of using the stage")
    p.add_argument("--thickness", type=float, help="Crystal thickness in micrometres, to work out birefringence")

    sub.add_parser("check", help="Check every part of the real bench")

    args = parser.parse_args(argv)

    if args.command == "serve":
        from .hardware import open_bench
        from .server import serve

        bench = open_bench(args.simulate)
        httpd = serve(bench, args.host, args.port)
        mode = "simulator" if bench.simulated else "hardware"
        print(f"Crystallyzer {__version__} ({mode}) on http://{'localhost' if args.host == '0.0.0.0' else args.host}:{args.port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            bench.close()
        return 0

    if args.command == "diffract":
        from . import diffraction, slides
        from .hardware import PiBench

        if args.simulate:
            if args.simulate not in slides.BY_ID:
                print(f"Unknown slide. Try one of: {', '.join(slides.BY_ID)}", file=sys.stderr)
                return 2
            img = slides.simulate(slides.BY_ID[args.simulate])
        else:
            img = PiBench().diffraction_image()
        r = diffraction.analyse(img)
        print(r.headline)
        print(f"  pattern: {r.pattern_fold}-fold. Slide: {r.crystal_fold}.")
        if r.a_um:
            print(f"  a = {r.a_um} µm, b = {r.b_um} µm, angle = {r.gamma_deg}°")
        if r.ring_um:
            print(f"  typical spacing about {r.ring_um} µm")
        if r.helix_angle_deg:
            print(f"  X opens ±{r.helix_angle_deg}° from the helix axis")
        print(f"  {r.explanation}")
        return 0

    if args.command == "polarize":
        from . import polarization
        from .crystals import BY_ID
        from .hardware import PiBench

        angles = [i * 15.0 for i in range(12)]
        if args.simulate:
            if args.simulate not in BY_ID:
                print(f"Unknown crystal. Try one of: {', '.join(BY_ID)}", file=sys.stderr)
                return 2
            c = BY_ID[args.simulate]
            frames = [polarization.stage_view(c, a) for a in angles]
            thickness = args.thickness or c.flake_um
        else:
            bench = PiBench()
            frames = [bench.stage_image(a) for a in angles]
            thickness = args.thickness
        r = polarization.analyse(frames, angles, thickness)
        print(r.headline)
        print(f"  {r.explanation}")
        if r.retardation_nm:
            print(f"  retardation about {r.retardation_nm:g} nm" + (f", so birefringence about {r.birefringence}" if r.birefringence else ""))
        return 0

    if args.command == "check":
        from .hardware import PiBench

        bench = PiBench()
        st = bench.status()
        for part, ok in st.parts.items():
            print(f"  {'ok  ' if ok else 'FAIL'} {part}")
        for problem in st.problems:
            print(f"  ! {problem}")
        print(f"  sensors: {bench.sensors()}")
        bench.close()
        return 0 if not st.problems else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
