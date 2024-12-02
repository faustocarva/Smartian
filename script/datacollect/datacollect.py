import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

class DataCollect():

    def __init__(self) -> None:
        print("")
    
    def duplicate(self, csv):
        df = pd.read_csv(csv)

        # Find the global maximum value of total_seeds
        max_total_seeds = df['total_seeds'].max()

        # Normalize the total_duplicate_seeds and total_seeds by the global max
        df['duplicate_percentage'] = (df['total_duplicate_seeds'] / max_total_seeds) * 100
        df['duplicate_rate'] = (df['total_duplicate_seeds'] / max_total_seeds)

        df['performance_score'] = df['total_seeds'] * (1 - df['duplicate_rate'])
        
        # Normalize Performance Score to 0-100
        min_score = df['performance_score'].min()
        max_score = df['performance_score'].max()
        df['normalized_performance_score'] = (
            (df['performance_score'] - min_score) / (max_score - min_score) * 100
        )
        
        result = (
            df.groupby(['model', 'temperature'])
            #df.groupby(['model'])            
            .apply(lambda group: pd.Series({
                'duplicate_percentage': group['duplicate_percentage'].mean(),
                'performance_score': group['normalized_performance_score'].mean(),
                'mean_seeds': round(group['total_seeds'].mean())  # Calculate mean number of seeds
            }))
            .reset_index()            
        )        
        
        result['uniq_percentage'] = 100 - result["duplicate_percentage"]
        
        result = result.sort_values(by=['performance_score'], ascending=False)
        print(result)
        
        result = result.sort_values(by=['model', 'temperature'], ascending=False)        
        plt.figure(figsize=(10, 6))

        # Round values
        result['duplicate_percentage'] = result['duplicate_percentage'].round(2)
        result['performance_score'] = result['performance_score'].round(2)
        result['mean_seeds'] = result['mean_seeds'].round(2)

        # Line Plot
        plt.figure(figsize=(10, 6))

        # Plot each model's grouped data
        for model in result['model'].unique():
            model_data = result[result['model'] == model]
            plt.plot(
                model_data['temperature'],
                model_data['performance_score'],
                label=f'Model {model}',
                marker='o',  # Add markers at each point
                linestyle='-',  # Solid line
                linewidth=2
            )

        # Labels and title
        plt.title('Seed unique/capacity generation ratio vs Temperature', fontsize=16)
        plt.xlabel('Temperature', fontsize=14)
        plt.ylabel('Seed unique/capacity generation ratio (%)', fontsize=14)
        plt.xlim(0.0, 1.2)
        plt.ylim(0, 100)
        plt.grid(alpha=0.3)
        plt.legend(fontsize=12, loc='best')

        # Show plot
        plt.tight_layout()
        plt.savefig('scatter_plot.png', dpi=300)
        
    def valid(self, csv):
        df = pd.read_csv(csv)

        # Find the global maximum value of total_seeds
        max_total_seeds = df['total_seeds'].max()
        max_total_args_in_seeds = df['total_args_in_seeds'].max()
        max_total_functions_in_seeds = df['total_functions_in_seeds'].max()
        print(max_total_args_in_seeds,max_total_functions_in_seeds,max_total_seeds)
        
        df['invalid_args_in_seeds'] = (df['total_invalid_args_in_seeds'] / max_total_args_in_seeds) * 100
        df['invalid_functions_in_seeds'] = (df['total_invalid_function_in_seeds'] / max_total_functions_in_seeds) * 100

        result = (
            df.groupby(['model', 'temperature'])
            #df.groupby(['model'])            
            .apply(lambda group: pd.Series({
                'invalid_args_in_seeds': group['invalid_args_in_seeds'].mean(),
                'invalid_functions_in_seeds': group['invalid_functions_in_seeds'].mean(),
            }))
            .reset_index()            
        )        
        
        result = result.sort_values(by=['model', 'temperature'], ascending=False)
        print(result)

    def coverage(self, csv):
        df = pd.read_csv(csv)
        average_covered_instructions = df.groupby(['model', 'temperature'])['coveredInstructions'].mean().reset_index()
        average_covered_instructions.rename(columns={'coveredInstructions': 'averageCoveredInstructions'}, inplace=True)
        average_covered_instructions = average_covered_instructions.sort_values(by=['averageCoveredInstructions'], ascending=False)
        print(average_covered_instructions)

        average_covered_edges = df.groupby(['model', 'temperature'])['coveredEdges'].mean().reset_index()
        average_covered_edges.rename(columns={'coveredEdges': 'averageCoveredEdges'}, inplace=True)
        average_covered_edges = average_covered_edges.sort_values(by=['averageCoveredEdges'], ascending=False)
        print(average_covered_edges)
        
        average_defusechain = df.groupby(['model', 'temperature'])['coveredDefUseChains'].mean().reset_index()
        average_defusechain.rename(columns={'coveredDefUseChains': 'averageCoveredDefUseChains'}, inplace=True)
        average_defusechain = average_defusechain.sort_values(by=['averageCoveredDefUseChains'], ascending=False)
        print(average_defusechain)
        
        average_bugsfound = df.groupby(['model', 'temperature'])['bugsFound'].mean().reset_index()
        average_bugsfound.rename(columns={'bugsFound': 'averageBugsFound'}, inplace=True)
        average_bugsfound = average_bugsfound.sort_values(by=['averageBugsFound'], ascending=False)
        print(average_bugsfound)