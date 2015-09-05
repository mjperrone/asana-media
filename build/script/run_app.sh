cd /opt/asana-media/
. conf.sh
gunicorn --bind 0.0.0.0:8000 asana-media.asana-media:app
