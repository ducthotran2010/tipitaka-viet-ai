set -x

fly deploy . --image $(fly image show --app tipitaka-viet-postgres --json | jq -r '.[0].Repository + ":" + .[0].Tag')