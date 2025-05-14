curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync

git config --global user.email "noreply@github.com"
git config --global user.name "Bot"

zip -r gaims_preedit.zip . -x "*.venv*" -x "*.git*"