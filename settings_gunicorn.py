import os
import multiprocessing

work_home = os.path.dirname(os.path.abspath(__file__))
run_home = os.path.join(work_home, "run")
log_home = os.path.join(work_home, "log")
if not os.path.isdir(run_home):
    os.mkdir(run_home)
if not os.path.isdir(log_home):
    os.mkdir(log_home)

proc_name = "moviebox_upload"

bind = "unix:{}".format(os.path.join(run_home, "{}.sock".format(proc_name)))
workers = multiprocessing.cpu_count() * 2
threads = 100
worker_class = "gevent"

daemon = False
reload = False

pidfile = os.path.join(run_home, "{}.pid".format(proc_name))

# Logging config
logging = os.path.join(log_home, "gun_access.log")
errorlog = os.path.join(log_home, "gun_error.log")
