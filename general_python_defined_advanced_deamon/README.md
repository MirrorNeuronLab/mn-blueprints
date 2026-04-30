# General Python Defined Advanced Deamon

This blueprint is authored as pure Python with `mn_sdk` decorators and compiles to a
live daemon bundle. The final Python reducer emits a daemon event and stores state
instead of completing the job.

```bash
python3 generate_bundle.py --quick-test
mn run .
```
