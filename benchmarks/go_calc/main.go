package main

import (
	"fmt"
	"os"
	"strconv"
)

type CalcResult struct {
	Count int
	Sum   float64
	Mean  float64
	Min   float64
	Max   float64
}

func ComputeStats(numbers []float64) CalcResult {
	if len(numbers) == 0 {
		return CalcResult{}
	}
	sum := 0.0
	min := numbers[0]
	max := numbers[0]
	for _, n := range numbers {
		sum += n
		if n < min {
			min = n
		}
		if n > max {
			max = n
		}
	}
	return CalcResult{
		Count: len(numbers),
		Sum:   sum,
		Mean:  sum / float64(len(numbers)),
		Min:   min,
		Max:   max,
	}
}

func ReverseString(s string) string {
	r := []rune(s)
	for i, j := 0, len(r)-1; i < len(r)/2; i, j = i+1, j-1 {
		r[i], r[j] = r[j], r[i]
	}
	return string(r)
}

func printHelp() {
	fmt.Println("Usage: aegis_sample <command> [args...]")
	fmt.Println("Commands:")
	fmt.Println("  stats <num1> <num2> ...  Compute statistical summary")
	fmt.Println("  reverse <string>         Reverse a given string")
	fmt.Println("  version                  Print version")
}

func main() {
	if len(os.Args) < 2 {
		printHelp()
		os.Exit(1)
	}

	command := os.Args[1]

	switch command {
	case "version":
		fmt.Println("aegis_sample v1.0.0")
	case "help", "-h", "--help":
		printHelp()
		os.Exit(0)
	case "reverse":
		if len(os.Args) < 3 {
			fmt.Fprintln(os.Stderr, "Error: reverse requires a string")
			os.Exit(1)
		}
		fmt.Println(ReverseString(os.Args[2]))
	case "stats":
		if len(os.Args) < 3 {
			fmt.Fprintln(os.Stderr, "Error: stats requires at least one number")
			os.Exit(1)
		}
		var nums []float64
		for _, arg := range os.Args[2:] {
			val, err := strconv.ParseFloat(arg, 64)
			if err != nil {
				fmt.Fprintf(os.Stderr, "Error: invalid number '%s'\n", arg)
				os.Exit(2)
			}
			nums = append(nums, val)
		}
		res := ComputeStats(nums)
		fmt.Printf("count: %d, sum: %.2f, mean: %.2f, min: %.2f, max: %.2f\n",
			res.Count, res.Sum, res.Mean, res.Min, res.Max)
	default:
		fmt.Fprintf(os.Stderr, "Unknown command: %s\n", command)
		printHelp()
		os.Exit(1)
	}
}
