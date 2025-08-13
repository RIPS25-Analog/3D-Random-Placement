# Run a for loop 30 times to call the generate_data.py script using different seeds
for i in {8..19}
do
    echo "Running iteration $i"
    python3 generate_data.py --seed $i
    if [ $? -ne 0 ]; then
        echo "Error occurred in iteration $i"
        exit 1
    fi
    echo "Iteration $i completed successfully"
done
