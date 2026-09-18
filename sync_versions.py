# GEÇİCİ: Bu dosya, KraptorSync workflow'unun Python adımını mod denetim motoruna
# yönlendirmek için arena/01a0b5c1-kitsugi-plugins dalında oluşturuldu.
import runpy, os
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "McModAudit", "audit_runner.py"), run_name="__main__")
