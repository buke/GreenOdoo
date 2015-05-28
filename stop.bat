title GreenOdoo - www.GreenOpenERP.com
COLOR 0A
"%CD%"\runtime\bin\pv.exe -f -k python-oe.exe -q
"%CD%"\runtime\pgsql\bin\pg_ctl -D "%CD%"\runtime\pgsql\data -l "%CD%"\runtime\pgsql\logfile --silent --mode fast
"%CD%"\runtime\bin\pv.exe -f -k postgres.exe -q
