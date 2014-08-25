from thatsDEM import report
import os
here=os.path.dirname(__file__)
try:
	os.remove(os.path.join(here,"dhmqc.sqlite"))
except:
	pass
report.create_local_datasource()
