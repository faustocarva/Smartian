Gera arquivo com total de instruções
for dir in ./B1/\*; do (poetry run genai4fuzz count_total_ins "$dir">>B1-ins.csv); done
