NAME := Gomoku
SOURCES := gomoku_launcher.sh $(wildcard ai/*.py) $(wildcard game/*.py)

.PHONY: all clean fclean re

all: $(NAME)

$(NAME): $(SOURCES)
	cp gomoku_launcher.sh $(NAME)
	chmod +x $(NAME)

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache

fclean: clean
	rm -f $(NAME)

re: fclean all
