# Standard library imports
import itertools
import os

# Third-party library imports
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import to_rgba
from scipy import stats
from scipy.stats import f_oneway
import matplotlib.gridspec as gridspec
from datacollect.utils.models import get_model_visualization_scheme
import genai4fuzz.utils.datafile as datafile

class DataCollect():    
    METRICS_HEADER = 'model,temperature,file,total_files,total_files_with_invalid_json,total_seeds,total_duplicate_seeds,total_seeds_with_invalid_struct,total_args_in_seeds,total_invalid_args_in_seeds,total_functions_in_seeds,total_invalid_function_in_seeds'.split(',')
    COVERAGE_HEADER = 'contract,temperature,transaction_index,model,seed_file,totalExecutions,deployFailCount,coveredEdges,coveredInstructions,coveredDefUseChains,bugsFound'.split(',')
    B1_TOTAL_COV_HEADER = 'contract,totalInstructions,totalEdges'.split(',')
    
    def __init__(self) -> None:
        print("")

    @staticmethod
    def format_model_name(name):
        model_name_map = {
            'llama3.3-70B': 'Llama3.3-70B',
            'llama3-70b': 'Llama3-70B',            
            'gpt4-0mini': 'GPT-4o-Mini',
            'gpt4omini': 'GPT-4o-Mini',         
            'gpt4.1mini': 'GPT-4.1-Mini',                     
            'llama3-8b': 'Llama3-8B',
            'mixtral-8x7b': 'Mixtral-8x7B',
            'gemini-1.5-flash': 'Gemini-1.5-Flash'
        }
        return model_name_map.get(name.lower(), name)

    def get_mean_valid_seeds_per_model(self, csv):
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)
        df['valid_seeds'] = df['total_seeds'] - df['total_duplicate_seeds'] - df['total_seeds_with_invalid_struct']         
        df['valid_seeds'] = df['valid_seeds'].replace(0, pd.NA)
        df['model'] = df['model'].apply(self.format_model_name)
        
        
        return (
            df.groupby(['model', 'temperature'])
            .apply(lambda group: pd.Series({
                'mean_valid_seeds': round(group['valid_seeds'].mean())
            }))
            .reset_index()            
        )        

    def fill_missing_experiments(self, df):
        """
        Fill in missing experiment combinations in a DataFrame, keeping only transaction indices 1-10
        and filling remaining values with 0.
        
        Parameters:
        df (pandas.DataFrame): Input DataFrame with experimental results
        
        Returns:
        pandas.DataFrame: Complete DataFrame with filtered combinations and 0 for missing values
        """
        # First filter the original DataFrame to keep only transaction_index 1-10
        df = df[df['transaction_index'].between(1, 10)]
        
        # Get unique values for each dimension

        models = df['model'].unique()
        temperatures = df['temperature'].unique()
        contracts = df['contract'].unique()
        transaction_indices = list(range(1, 11))  # Force transaction indices to be 1-10
        
        # Create all possible combinations
        index = pd.MultiIndex.from_product([contracts, temperatures, transaction_indices, models],
                                        names=['contract', 'temperature', 'transaction_index', 'model'])
        
        # Convert to DataFrame
        complete_df = pd.DataFrame(index=index).reset_index()
        
        # Merge with original data
        result = pd.merge(complete_df, df, 
                        on=['contract', 'temperature', 'transaction_index', 'model'],
                        how='left')
        
        # Sort the result for better readability
        result = result.sort_values(['contract', 'temperature', 'transaction_index', 'model'])
        
        # Reset index
        result = result.reset_index(drop=True)
        
        # Fill all numeric columns with 0
        numeric_columns = ['totalExecutions', 'deployFailCount', 'coveredEdges', 
                        'coveredInstructions', 'coveredDefUseChains', 'bugsFound']
        result[numeric_columns] = result[numeric_columns].fillna(0)
        
        # Fill seed_file with 'missing' if it exists in the DataFrame
        if 'seed_file' in result.columns:
            result['seed_file'] = result['seed_file'].fillna('missing')
            
        return result
        
    def load_coverage_data(self, csv):
        ins_file = datafile.load_data_file(csv)          
        df = pd.read_csv(ins_file, header=None, names=self.B1_TOTAL_COV_HEADER)
        return df
    
    def build_coverage_data(self, csv):
        executions_df = pd.read_csv(csv, header=None, names=self.COVERAGE_HEADER)        
        totals_df = self.load_coverage_data("B1-ins.csv")
        
        executions_df = self.fill_missing_experiments(executions_df)

        total_valid_seeds = executions_df.groupby(['model', 'temperature', 'contract']).size().reset_index(name='row_count')
        total_valid_seeds = total_valid_seeds.groupby(['model', 'temperature']).size().reset_index(name='seed_count').sort_values(by=['seed_count'], ascending=False)

        totals = executions_df.groupby(
            ['contract', 'model', 'temperature']
        ).size().reset_index(name='totalSeedsPerModelTemp')
    
        
        # Calculate mean values for each contract-model-temperature combination
        grouped_metrics = executions_df.groupby(
            ['contract', 'model', 'temperature']
        ).agg({
            'coveredInstructions': 'mean',
            'coveredEdges': 'mean',
            'bugsFound': 'mean',
            'coveredDefUseChains': 'mean',
            #'deployFailCount': ['mean', 'sum']
        }).reset_index()
        
        print(grouped_metrics.columns.to_list())  # Shows the index (can be Index or MultiIndex)
        print(totals.columns.to_list())
        
        
        grouped_metrics = grouped_metrics.merge(totals, on=['contract', 'model', 'temperature'])
                
        # Generate complete combination matrix
        unique_models = grouped_metrics['model'].unique()
        unique_temperatures = grouped_metrics['temperature'].unique()
        
        # Fill missing combinations with zeros
        new_rows = []
        for _, row in totals_df.iterrows():
            contract = row['contract']
            new_total_instructions = row['totalInstructions']
            new_total_edges = row['totalEdges']
            
            for model, temperature in itertools.product(unique_models, unique_temperatures):
                query_result = grouped_metrics.loc[
                    (grouped_metrics['contract'] == contract) &
                    (grouped_metrics['model'] == model) &
                    (grouped_metrics['temperature'] == temperature)].index
                    
                if query_result.empty:
                    new_rows.append({
                        'contract': contract,
                        'model': model,
                        'temperature': temperature,
                        'coveredInstructions': 0,
                        'coveredEdges': 0,
                        'bugsFound': 0,
                        'coveredDefUseChains': 0,
                        'totalInstructions': new_total_instructions,
                        'totalEdges': new_total_edges,
                        'totalSeedsPerModelTemp': 0
                    })
                else:
                    grouped_metrics.loc[query_result, 'totalInstructions'] = new_total_instructions
                    grouped_metrics.loc[query_result, 'totalEdges'] = new_total_edges
                
        return pd.concat([grouped_metrics, pd.DataFrame(new_rows)], ignore_index=True), total_valid_seeds
        
    def build_perf_score_seeds(self, csv):
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)

        # Find the global maximum value of total_seeds
        max_total_seeds = df['total_seeds'].max()
        
        df['valid_seeds'] = df['total_seeds'] - df['total_duplicate_seeds'] - df['total_seeds_with_invalid_struct']         
        #df['valid_seeds'] = df['valid_seeds'].replace(0, pd.NA)

        df['duplicate_percentage'] = (df['total_duplicate_seeds'] / max_total_seeds) * 100
        df['invalid_struct_percentage'] = (df['total_seeds_with_invalid_struct'] / max_total_seeds) * 100
        
        df['duplicate_rate'] = (df['total_duplicate_seeds'] / max_total_seeds)
        df['invalid_struct_rate'] = df['total_seeds_with_invalid_struct'] / max_total_seeds

        df['penalty_factor'] = (1 - df['duplicate_rate'] - df['invalid_struct_rate']).clip(lower=0)
        
        df['performance_score'] = df['total_seeds'] * df['penalty_factor']
        
        min_score = df['performance_score'].min()
        max_score = df['performance_score'].max()
        df['normalized_performance_score'] = (
            (df['performance_score'] - min_score) / (max_score - min_score) * 100
        )
        
        return df                    

    def build_perf_score_seeds_args_funcs_2(self, csv):
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)

        # Find the global maximum values
        max_total_seeds = df['total_seeds'].max()
        max_total_args = df['total_args_in_seeds'].max()
        max_total_functions = df['total_functions_in_seeds'].max()

        # Calculate valid seeds
        df['valid_seeds'] = df['total_seeds'] - df['total_duplicate_seeds'] - df['total_seeds_with_invalid_struct']         
        df['valid_seeds'] = df['valid_seeds'].replace(0, pd.NA)

        # Calculate percentages for all metrics
        df['duplicate_percentage'] = (df['total_duplicate_seeds'] / max_total_seeds) * 100
        df['invalid_struct_percentage'] = (df['total_seeds_with_invalid_struct'] / max_total_seeds) * 100
        df['invalid_args_percentage'] = (df['total_invalid_args_in_seeds'] / max_total_args) * 100
        df['invalid_functions_percentage'] = (df['total_invalid_function_in_seeds'] / max_total_functions) * 100

        # Calculate rates for penalty factor
        df['duplicate_rate'] = df['total_duplicate_seeds'] / max_total_seeds
        df['invalid_struct_rate'] = df['total_seeds_with_invalid_struct'] / max_total_seeds
        df['invalid_args_rate'] = df['total_invalid_args_in_seeds'] / max_total_args
        df['invalid_functions_rate'] = df['total_invalid_function_in_seeds'] / max_total_functions

        # Calculate combined penalty factor including all metrics
        # df['penalty_factor'] = (1 - 0.4*df['duplicate_rate'] - 
        #                     0.4*df['invalid_struct_rate'] - 
        #                     0.1*df['invalid_args_rate'] - 
        #                     0.1*df['invalid_functions_rate']).clip(lower=0)

        df['penalty_factor'] = (1 - df['duplicate_rate'] - 
                            df['invalid_struct_rate']).clip(lower=0)

        df['performance_score'] = df['total_seeds'] * df['penalty_factor']

        # # Normalize performance score
        # min_score = df['performance_score'].min()
        # max_score = df['performance_score'].max()
        # df['normalized_performance_score'] = (
        #     (df['performance_score'] - min_score) / (max_score - min_score) * 100
        # )
        
        # [Previous code remains identical until performance_score calculation]
        df['performance_score'] = df['total_seeds'] * df['penalty_factor']

        # First, let's group experiments by model and temperature and calculate mean values
        grouped_df = df.groupby(['model', 'temperature']).agg({
            'performance_score': 'mean',
            'total_seeds': 'mean'  # We'll need this for relative performance calculation
        }).reset_index()

        # Calculate statistical measures using the grouped data
        mean_score = grouped_df['performance_score'].mean()
        std_score = grouped_df['performance_score'].std()
        
        # Calculate z-scores for grouped data
        grouped_df['z_score'] = (grouped_df['performance_score'] - mean_score) / std_score
        
        # Calculate relative performance against theoretical maximum for grouped data
        theoretical_max = df['total_seeds'].max()  # Using max from original data as theoretical maximum
        grouped_df['relative_performance'] = (grouped_df['performance_score'] / theoretical_max) * 100
        
        # Calculate percentile ranks for grouped results
        grouped_df['percentile_rank'] = grouped_df['performance_score'].rank(pct=True) * 100
        
        # Calculate confidence intervals using standard error of the mean from the original grouped data
        confidence_level = 0.95
        z_critical = stats.norm.ppf((1 + confidence_level) / 2)
        
        # Calculate standard error and confidence intervals for each group
        ci_data = []
        for (model, temp), group in df.groupby(['model', 'temperature']):
            n_experiments = len(group)
            group_std = group['performance_score'].std()
            std_error = group_std / np.sqrt(n_experiments)
            
            relative_std_error = (std_error / theoretical_max) * 100
            ci_lower = (group['performance_score'].mean() / theoretical_max * 100) - (z_critical * relative_std_error)
            ci_upper = (group['performance_score'].mean() / theoretical_max * 100) + (z_critical * relative_std_error)
            
            ci_data.append({
                'model': model,
                'temperature': temp,
                'ci_lower': ci_lower,
                'ci_upper': ci_upper
            })
        
        ci_df = pd.DataFrame(ci_data)
        grouped_df = grouped_df.merge(ci_df, on=['model', 'temperature'])
        
        # Calculate p-values for z-scores
        grouped_df['p_value'] = 2 * (1 - stats.norm.cdf(abs(grouped_df['z_score'])))
        
        # Generate statistical reports for each model and temperature combination
        reports = []
        for _, row in grouped_df.iterrows():
            n_experiments = len(df[(df['model'] == row['model']) & 
                                (df['temperature'] == row['temperature'])])
            
            significance_text = "significantly above average (p < 0.05)" if row['p_value'] < 0.05 else \
                            "not significantly different from average (p ≥ 0.05)"
            
            report = (
                f"Model {row['model']} at temperature {row['temperature']} "
                f"(averaged across {n_experiments} experiments) achieved a "
                f"relative performance of {row['relative_performance']:.1f}% "
                f"(95% CI: {row['ci_lower']:.1f}%-{row['ci_upper']:.1f}%), "
                f"placing it in the {row['percentile_rank']:.1f}th percentile "
                f"of all tested configurations. The z-score of {row['z_score']:.2f} "
                f"indicates the performance was {significance_text}."
            )
            reports.append(report)
        
        # Store reports and normalized scores in original DataFrame
        grouped_df['statistical_report'] = reports
        grouped_df['normalized_performance_score'] = stats.norm.cdf(grouped_df['z_score']) * 100
        
        # Print reports
        print("\nDetailed Statistical Analysis of Grouped Experiments:")
        print("=" * 80)
        for report in reports:
            print("\n" + report)
            print("-" * 80)
        
        # Merge the grouped statistics back into the original DataFrame
        df = df.merge(
            grouped_df[['model', 'temperature', 'normalized_performance_score', 'statistical_report']], 
            on=['model', 'temperature']
        )
        
        return df    
        
    def build_perf_score_seeds_args_funcs(self, csv):
            df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)

            # Find the global maximum values
            max_total_seeds = df['total_seeds'].max()
            max_total_args = df['total_args_in_seeds'].max()
            max_total_functions = df['total_functions_in_seeds'].max()

            # Calculate valid seeds
            df['valid_seeds'] = df['total_seeds'] - df['total_duplicate_seeds'] - df['total_seeds_with_invalid_struct']         
            df['valid_seeds'] = df['valid_seeds'].replace(0, pd.NA)

            # Calculate percentages for all metrics
            df['duplicate_percentage'] = (df['total_duplicate_seeds'] / max_total_seeds) * 100
            df['invalid_struct_percentage'] = (df['total_seeds_with_invalid_struct'] / max_total_seeds) * 100
            df['invalid_args_percentage'] = (df['total_invalid_args_in_seeds'] / max_total_args) * 100
            df['invalid_functions_percentage'] = (df['total_invalid_function_in_seeds'] / max_total_functions) * 100

            # Calculate rates for penalty factor
            df['duplicate_rate'] = df['total_duplicate_seeds'] / max_total_seeds
            df['invalid_struct_rate'] = df['total_seeds_with_invalid_struct'] / max_total_seeds
            df['invalid_args_rate'] = df['total_invalid_args_in_seeds'] / max_total_args
            df['invalid_functions_rate'] = df['total_invalid_function_in_seeds'] / max_total_functions

            # Calculate combined penalty factor including all metrics
            df['penalty_factor'] = (1 - df['duplicate_rate'] - 
                                df['invalid_struct_rate'] - 
                                0.01*df['invalid_args_rate'] - 
                                0.01*df['invalid_functions_rate']).clip(lower=0)

            df['performance_score'] = df['total_seeds'] * df['penalty_factor']

            # Normalize performance score
            min_score = df['performance_score'].min()
            max_score = df['performance_score'].max()
            df['normalized_performance_score'] = (
                (df['performance_score'] - min_score) / (max_score - min_score) * 100
            )
            
            return df
        
    def total_files(self, csv):
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)
        
        df['valid_files'] = df['total_files'] - df['total_files_with_invalid_json']
        df['valid_files'] = df['valid_files'].replace(0, pd.NA)
                  
        result = (
            df.groupby(['model', 'temperature'])
            .apply(lambda group: pd.Series({
                'mean_files': round(group['valid_files'].mean())
            }))
            .reset_index()            
        )        
        plt.figure(figsize=(10, 6))

        for model in result['model'].unique():
            model_data = result[result['model'] == model]
            plt.plot(
                model_data['temperature'],
                model_data['mean_files'],
                label=f'{model}',
                marker='o',  # Add markers at each point
                linestyle='-',  # Solid line
                linewidth=2
            )

        # Labels and title
        plt.title('Mean total files generated by Model per Temperature', fontsize=16)
        plt.xlabel('Temperature', fontsize=14)
        plt.ylabel('Total files', fontsize=14)
        
        #plt.ylim(0, 58)        
        plt.xlim(0.0, 1.2)
        plt.grid(alpha=0.3)
        plt.legend(fontsize=12, loc='best')

        plt.tight_layout()
        plt.savefig('plot_total_files_by_model_temperature.pdf', bbox_inches="tight")        
        
    def total_seeds(self, csv):
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)
                
        max_total_seeds = df['total_seeds'].max()                
        result = (
            df.groupby(['model', 'temperature'])
            .apply(lambda group: pd.Series({
                'mean_seeds': round(group['total_seeds'].mean())
            }))
            .reset_index()            
        )        
        plt.figure(figsize=(10, 6))

        for model in result['model'].unique():
            model_data = result[result['model'] == model]
            plt.plot(
                model_data['temperature'],
                model_data['mean_seeds'],
                label=f'{model}',
                marker='o',  # Add markers at each point
                linestyle='-',  # Solid line
                linewidth=2
            )

        # Labels and title
        plt.title('Mean total seeds generated by Model per Temperature', fontsize=16)
        plt.xlabel('Temperature', fontsize=14)
        plt.ylabel('Total seeds', fontsize=14)
        
        plt.ylim(0, max_total_seeds)        
        plt.xlim(0.0, 1.2)
        plt.grid(alpha=0.3)
        plt.legend(fontsize=12, loc='best')

        plt.tight_layout()
        plt.savefig('plot_total_seeds_by_model_temperature.pdf', bbox_inches="tight")        
                
        ########################################################################################################
        
        df['valid_seeds'] = df['total_seeds'] - df['total_duplicate_seeds'] - df['total_seeds_with_invalid_struct']         
        df['valid_seeds'] = df['valid_seeds'].replace(0, pd.NA)
        
        result_by_model_temp = (
            df.groupby(['model', 'temperature'])
            .apply(lambda group: pd.Series({
                'mean_seeds': round(group['valid_seeds'].mean())
            }))
            .reset_index()
        )
        
        result_by_model = (
            df.groupby(['model'])
            .apply(lambda group: pd.Series({
                'mean_seeds': round(group['valid_seeds'].mean())
            }))
            .reset_index()
        )
        result_by_model = result_by_model.sort_values(by=['mean_seeds'], ascending=False)
        print(result_by_model)

        plt.figure(figsize=(10, 6))

        line_data = {}
        for model in result_by_model_temp['model'].unique():
            model_data_temp = result_by_model_temp[result_by_model_temp['model'] == model]
            line, =  plt.plot(
                model_data_temp['temperature'],
                model_data_temp['mean_seeds'],
                label=f'{model}',
                marker='o',
                linestyle='-',  # Solid line
                linewidth=2,
            )
            line_data[model] = {
                'line': line,
                'color': line.get_color()
            }

        # Plot data grouped by model only
        for model in result_by_model['model']:
            mean_seed = result_by_model[result_by_model['model'] == model]['mean_seeds'].values[0]
            plt.axhline(
                y=mean_seed,
                linestyle='--',
                color=line_data[model]['color']  
            )

        # Labels and title
        plt.title('Valid Generated Seeds per Model & Temperature', fontsize=16)
        plt.xlabel('Temperature', fontsize=14)
        plt.ylabel('Total Seeds', fontsize=14)
        
        plt.ylim(0, max_total_seeds)
        plt.xlim(0.0, 1.2)
        plt.grid(alpha=0.3)
        plt.legend(fontsize=10, loc='best')

        # Show plot
        plt.tight_layout()                
        
        plt.savefig('plot_total_efective_seeds_by_model_temperature.pdf', bbox_inches="tight")
    
    def best_model_temp_metrics(self, csv):
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)
        
        """Process the raw metrics data to calculate performance metrics."""
        # Define the desired order of models
        model_order = ["Llama3.3-70B", "Llama3-70B", "gemini-1.5-flash", "mixtral-8x7b", "gpt4omini", "Llama3-8B"]
        
        # Find the maximum possible seeds across all models
        max_seeds = df.groupby('model')['total_seeds'].max().max()
        
        # Group by model and temperature
        grouped = df.groupby(['model', 'temperature']).agg({
            'total_seeds': 'mean',  # Average seeds per run
            'total_args_in_seeds': 'sum',
            'total_invalid_args_in_seeds': 'sum',
            'total_functions_in_seeds': 'sum',
            'total_invalid_function_in_seeds': 'sum',
            'file': 'count'  # Count number of runs
        }).reset_index()

        # Ensure the model column follows the desired order
        grouped['model'] = pd.Categorical(grouped['model'], categories=model_order, ordered=True)
        grouped = grouped.sort_values(['model', 'temperature'])

        # Calculate seed generation rate
        grouped['seed_generation_rate'] = (grouped['total_seeds'] / max_seeds) * 100

        # Calculate separate error rates for args and functions
        grouped['args_error_rate'] = (
            grouped['total_invalid_args_in_seeds'] / grouped['total_args_in_seeds'] * 100
        )
        grouped['functions_error_rate'] = (
            grouped['total_invalid_function_in_seeds'] / grouped['total_functions_in_seeds'] * 100
        )
        grouped['combined_error_rate'] = (
            (grouped['total_invalid_args_in_seeds'] / grouped['total_args_in_seeds'] +
            grouped['total_invalid_function_in_seeds'] / grouped['total_functions_in_seeds']) / 2 * 100
        )
        
        # Calculate scaled error rate
        grouped['scaled_error_rate'] = grouped['combined_error_rate'] * (max_seeds / grouped['total_seeds'])
        
        # Handle any infinite values
        grouped = grouped.replace([np.inf, -np.inf], np.nan)
        
        processed_data = grouped
                
        """Generate a detailed summary table of model performance."""
        summary = []
        
        for model in processed_data['model'].unique():
            model_data = processed_data[processed_data['model'] == model]
            best_temp_idx = model_data['scaled_error_rate'].idxmin()
            best_performance = model_data.loc[best_temp_idx]
            
            summary.append({
                'Model': model,
                'Best Temperature': best_performance['temperature'],
                'Seed Generation Rate (%)': best_performance['seed_generation_rate'],
                'Combined Error Rate (%)': best_performance['combined_error_rate'],
                'Scaled Error Rate': best_performance['scaled_error_rate'],
                'Args Error Rate (%)': best_performance['args_error_rate'],
                'Functions Error Rate (%)': best_performance['functions_error_rate']
            })
                
        # Generate and display summary table
        summary_table = pd.DataFrame(summary)
        print("\nModel Performance Summary:")
        print(summary_table.to_string(index=False))
        
        # Generate LaTeX table
        model_summaries = []
        
        for model in processed_data['model'].unique():
            model_data = processed_data[processed_data['model'] == model]
            avg_seed_rate = model_data['seed_generation_rate'].mean()
            best_temp_idx = model_data['combined_error_rate'].idxmin()
            best_temp = model_data.loc[best_temp_idx]
            
            model_summaries.append({
                'model': model,
                'seed_rate': avg_seed_rate,
                'best_temp': best_temp['temperature'],
                'error_rate': best_temp['combined_error_rate'],
                'scaled_error': best_temp['scaled_error_rate'],
                'args_error': best_temp['args_error_rate'],
                'func_error': best_temp['functions_error_rate']
            })
        
        # Generate LaTeX table
        latex_table = [
            "\\begin{table}[h]",
            "\\centering",
            "\\begin{tabular}{lcccccc}",
            "\\hline",
            "\\textbf{Model} & \\textbf{Seed Rate} & \\textbf{Best} & \\textbf{Combined} & \\textbf{Scaled} & \\textbf{Args} & \\textbf{Func} \\\\",
            "& \\textbf{(\\%)} & \\textbf{Temp} & \\textbf{Error (\\%)} & \\textbf{Error} & \\textbf{Error (\\%)} & \\textbf{Error (\\%)} \\\\",
            "\\hline"
        ]
        
        # Add data rows
        for summary in model_summaries:
            row = (
                f"{summary['model']} & "
                f"{summary['seed_rate']:.1f} & "
                f"{summary['best_temp']:.1f} & "
                f"{summary['error_rate']:.2f} & "
                f"{summary['scaled_error']:.2f} & "
                f"{summary['args_error']:.2f} & "
                f"{summary['func_error']:.2f} \\\\"
            )
            latex_table.append(row)
        
        # Add footer
        latex_table.extend([
            "\\hline",
            "\\end{tabular}",
            "\\caption{Comprehensive Model Performance Summary showing seed generation rates, "
            "optimal temperatures, and various error metrics. Args and Func Error show the "
            "breakdown of errors by argument validation and function validation respectively.}",
            "\\label{tab:model-performance}",
            "\\end{table}"
        ])
        
        print("\nLaTeX Table:")
        print('\n'.join(latex_table))

    def seed_args_and_funcs(self, csv):
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)                    
        # Format model names
        df['model'] = df['model'].apply(self.format_model_name)
        
        # Get the complete model scheme
        complete_model_scheme = get_model_visualization_scheme()
        
        # Extract the model order from the keys of the scheme
        model_order = list(complete_model_scheme.keys())        

        # Group by model and temperature
        grouped = df.groupby(['model', 'temperature']).agg({
            'total_args_in_seeds': 'sum',
            'total_invalid_args_in_seeds': 'sum',
            'total_functions_in_seeds': 'sum',
            'total_invalid_function_in_seeds': 'sum',
            'file': 'count'  # Count number of runs
        }).reset_index()

        # Ensure the model column follows the desired order
        grouped['model'] = pd.Categorical(grouped['model'], categories=model_order, ordered=True)
        grouped = grouped.sort_values(['model', 'temperature'])

        # Calculate error rates
        grouped['args_error_rate'] = (
            grouped['total_invalid_args_in_seeds'] / grouped['total_args_in_seeds'] * 100
        )

        grouped['functions_error_rate'] = (
            grouped['total_invalid_function_in_seeds'] / grouped['total_functions_in_seeds'] * 100
        )

        grouped['combined_error_rate'] = (
            (grouped['total_invalid_args_in_seeds'] / grouped['total_args_in_seeds'] +
            grouped['total_invalid_function_in_seeds'] / grouped['total_functions_in_seeds']) / 2 * 100
        )

        grouped['invalid_args_per_run'] = grouped['total_invalid_args_in_seeds'] / grouped['file']
        grouped['invalid_functions_per_run'] = grouped['total_invalid_function_in_seeds'] / grouped['file']


        # Get unique models from the data that are actually present
        unique_models = grouped['model'].unique()
        
        # Get the visualization scheme using our function
        model_scheme = get_model_visualization_scheme(unique_models)
    
        # Create visualizations for each metric
        metrics_to_plot = [
            ('args_error_rate', 'Arguments Error Rate (%)', 'Invalid Functions Arguments (%) By Temperature', 50),
            ('functions_error_rate', 'Functions Error Rate (%)', 'Invalid Functions (%) By Temperature', 50),
            # ('combined_error_rate', 'Combined Error Rate (%)', 'Combined Error Rate By Temperature', 100),
            # ('invalid_args_per_run', 'Total Invalid Arguments', 'Total Invalid Arguments By Temperature', 0),
            # ('invalid_functions_per_run', 'Total Invalid Functions', 'Total Invalid Functions By Temperature', 0)
        ]
        
        def plot_metric(data, metric, title, ylabel, ylim=0, figsize=(12, 8)):
            plt.figure(figsize=figsize)
            ax = plt.gca()
            

            for model in unique_models:
                model_data = data[data['model'] == model]
                # Skip if no data for this model
                if model_data.empty:
                    continue
                    
                # Get the color and marker for this model from our scheme
                color = model_scheme[model]["color"]
                marker = model_scheme[model]["marker"]
            
                
                # Main line with markers
                plt.plot(model_data['temperature'], 
                        model_data[metric], 
                        marker=marker,
                        markersize=12,
                        linewidth=3,
                        color=color,
                        label=model,
                        alpha=0.8)
                
                # Shadow effect
                plt.plot(model_data['temperature'], 
                        model_data[metric],
                        color='gray',
                        linewidth=4,
                        alpha=0.2,
                        zorder=-1)

            # Styling
            plt.xlabel('Temperature', fontsize=14, fontweight='bold')
            plt.ylabel(ylabel, fontsize=14, fontweight='bold')
            plt.title(title, fontweight='bold', fontsize=16, pad=20)

            # Grid and background
            plt.grid(True, linestyle='--', alpha=0.7)
            ax.set_facecolor('#f8f9fa')
            ax.tick_params(axis='both', which='major', labelsize=12)

            # Enhanced legend
            legend = plt.legend(
                title="Models",
                title_fontsize=12,
                fontsize=11,
                loc='best',
                frameon=True,
                fancybox=True,
                shadow=True,
                borderpad=1
            )
            legend.get_frame().set_facecolor('white')
            legend.get_frame().set_alpha(0.9)

            # Spines
            for spine in ax.spines.values():
                spine.set_edgecolor('#cccccc')
                spine.set_linewidth(1.5)

            if ylim > 0:
                plt.ylim(0, ylim)

            plt.tight_layout()
            return plt
        
        for metric, ylabel, title, ylim in metrics_to_plot:
            plot = plot_metric(grouped, metric, title, ylabel, ylim)
            plot.savefig(f'{metric}.pdf', bbox_inches='tight', dpi=600)
            plt.close()
        
    def total_files_seeds_by_model_temperature(self, csv):
        # Read and process data
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)
        
        # Calculate means grouped by model and temperature
        grouped_df = df.groupby(['model', 'temperature']).agg({
            'total_seeds': 'mean',  # Average seeds per run            
            'total_files': 'mean',
            'total_files_with_invalid_json': 'mean',
            'total_seeds': 'mean',
            'total_duplicate_seeds': 'mean',
            'total_seeds_with_invalid_struct': 'mean',
            'file': 'count'  # Count number of runs
            
        }).reset_index()

        # Calculate seed generation rate
        max_seeds = df.groupby('model')['total_seeds'].max().max()        
        grouped_df['seed_generation_rate'] = (grouped_df['total_seeds'] / max_seeds) * 100

        # Calculate mean total_files - total_files_with_invalid_json
        grouped_df['valid_files_mean'] = grouped_df['total_files'] - grouped_df['total_files_with_invalid_json']
        grouped_df['valid_seeds'] = grouped_df['total_seeds'] - grouped_df['total_duplicate_seeds'] - grouped_df['total_seeds_with_invalid_struct']    
        
        # Set figure size
        fig, ax1 = plt.subplots(figsize=(10, 6))
        
        # Set style
        sns.set_style("whitegrid")
        
        # Create plot for total seeds
        models = grouped_df['model'].unique()
        markers = ['+','o', 'D', 's', '^', 'v']  # More distinct markers        
        
        # Define color palette
        color_palette = sns.color_palette("tab10", len(models))  # Use seaborn's tab10 palette
        
        handles1 = []
        labels1 = []
        handles2 = []
        labels2 = []
        
        for model, marker, color in zip(models, markers, color_palette):
            model_data = grouped_df[grouped_df['model'] == model]
            # Plot seeds vs temperature on primary y-axis
            line1, = ax1.plot(model_data['temperature'], 
                            model_data['valid_seeds'], 
                            marker=marker,
                            markersize=10,
                            linewidth=2,
                            color=color,  # Use color from palette
                            label=f"Valid Seeds - {model}")
            handles1.append(line1)
            labels1.append(f"{model}")
        
        # Customize primary y-axis
        ax1.set_xlabel('Temperature')
        ax1.set_ylabel('Total Valid Seeds Generated', fontweight='bold')
        ax1.tick_params(axis='y')
        ax1.set_title('Total Valid Seeds and Total Contracts with Generated Seeds vs Temperature by Model',  fontweight='bold', fontsize=12)
        
        # Create secondary y-axis for valid files mean
        ax2 = ax1.twinx()
        
        for model, marker, color in zip(models, markers, color_palette):
            model_data = grouped_df[grouped_df['model'] == model]
            
            # Create a slightly lighter version of the color for the dashed lines
            lighter_color = mcolors.to_rgba(color, alpha=0.6)  # Slightly lighter by adjusting the alpha
            
            # Plot valid files mean vs temperature on secondary y-axis with a lighter color
            line2, = ax2.plot(model_data['temperature'], 
                            model_data['valid_files_mean'], 
                            marker=marker,
                            markersize=10,
                            linewidth=2,
                            linestyle='--',  # Dashed line style
                            color=lighter_color,  # Slightly lighter color for dashed lines
                            label=f"Valid Files - {model}")
            # handles2.append(line2)
            # labels2.append(f"Valid Files - {model}")
        
        # Customize secondary y-axis
        ax2.set_ylabel('Total Valid Files', fontweight='bold')
        ax2.tick_params(axis='y')
        
        # Combine handles and labels for both axes, and sort by color
        handles = handles1 + handles2
        labels = labels1 + labels2
        
        # Sorting by color (lightness)
        sorted_handles_labels = sorted(zip(handles, labels), key=lambda x: x[0].get_color())
        sorted_handles, sorted_labels = zip(*sorted_handles_labels)
        
        # Add combined legend
        ax1.legend(sorted_handles, sorted_labels, bbox_to_anchor=(1.11, 1), loc='upper left')
        
        # Add annotations for line styles
        fig.text(0.97, 0.62,
                'Solid lines: Valid Seeds\nDashed lines: Valid Files',
                fontsize=10,
                ha='right',
                bbox=dict(facecolor='white',
                        alpha=0.9,
                        edgecolor='gray',
                        boxstyle='round,pad=0.5'))    
        
        # Adjust layout
        plt.tight_layout()
        plt.savefig('plot_total_files_seeds_by_model_temperature.pdf', bbox_inches="tight")             
                        
    def total_files_seeds_by_model_side_temperature(self, csv):
        ########################################################################################################
        # Read and process data
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)        
        
        # Calculate means grouped by model and temperature
        grouped_df = df.groupby(['model', 'temperature']).agg({
            'total_files': 'mean',
            'total_files_with_invalid_json': 'mean',
            'total_seeds': 'mean',
            'total_duplicate_seeds': 'mean',
            'total_seeds_with_invalid_struct': 'mean'
        }).reset_index()

        # Calculate valid files and seeds
        max_seeds = df.groupby('model')['total_seeds'].max().max()                
        grouped_df['valid_files_mean'] = grouped_df['total_files'] - grouped_df['total_files_with_invalid_json']
        grouped_df['valid_seeds'] = grouped_df['total_seeds'] - grouped_df['total_duplicate_seeds'] - grouped_df['total_seeds_with_invalid_struct']    
        
        # Calculate percentage of valid files
        grouped_df['valid_files_percentage'] = (grouped_df['valid_files_mean'] / grouped_df['total_files']) * 100
        
        # Create figure with shared y-axis
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
        
        models = grouped_df['model'].unique()
        markers = ['+','o', 'D', 's', '^', 'v']  # More distinct markers
        color_palette = sns.color_palette("tab10", len(models))  # Original color palette
        
        # First plot: Valid Seeds
        for model, marker, color in zip(models, markers, color_palette):
            model_data = grouped_df[grouped_df['model'] == model]
            line = ax1.plot(model_data['temperature'], 
                        model_data['valid_seeds'], 
                        marker=marker,
                        markersize=12,
                        linewidth=3,
                        color=color,
                        label=f"{model}",
                        alpha=0.8)
            
            # Add shadow effect to lines
            ax1.plot(model_data['temperature'], 
                    model_data['valid_seeds'],
                    color='gray',
                    linewidth=4,
                    alpha=0.2,
                    zorder=-1)
        
        ax1.set_xlabel('Temperature', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Total Valid Seeds', fontsize=12, fontweight='bold')
        ax1.set_title('Total Valid Seeds Generated vs Temperature Across Models', 
                    fontweight='bold', 
                    fontsize=14,
                    pad=20)
        ax1.grid(True, linestyle='--', alpha=0.7)
        ax1.tick_params(axis='both', which='major', labelsize=10)
        
        # Add light background color to first plot
        ax1.set_facecolor('#f8f9fa')
        
        # Second plot: Valid Files Percentage
        for model, marker, color in zip(models, markers, color_palette):
            model_data = grouped_df[grouped_df['model'] == model]
            line = ax2.plot(model_data['temperature'], 
                        model_data['valid_files_percentage'], 
                        marker=marker,
                        markersize=12,
                        linewidth=3,
                        color=color,
                        label=f"{model}",
                        alpha=0.8)
            
            # Add shadow effect to lines
            ax2.plot(model_data['temperature'], 
                    model_data['valid_files_percentage'],
                    color='gray',
                    linewidth=4,
                    alpha=0.2,
                    zorder=-1)
        
        ax2.set_xlabel('Temperature', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Percentage of Valid Files (%)', fontsize=12, fontweight='bold')
        ax2.set_title('Percentage of Valid Files vs Temperature Across Models', 
                    fontweight='bold', 
                    fontsize=14,
                    pad=20)
        ax2.grid(True, linestyle='--', alpha=0.7)
        ax2.tick_params(axis='both', which='major', labelsize=10)
        
        # Add light background color to second plot
        ax2.set_facecolor('#f8f9fa')
        
        # Enhance legend
        for ax in [ax1, ax2]:
            legend = ax.legend(bbox_to_anchor=(0.5, -0.15),
                            loc='upper center',
                            ncol=len(models),
                            fontsize=10,
                            frameon=True,
                            fancybox=True,
                            shadow=True)
            legend.get_frame().set_facecolor('white')
            legend.get_frame().set_alpha(0.9)
        
        # Add subtle border around the entire figure
        for ax in [ax1, ax2]:
            for spine in ax.spines.values():
                spine.set_edgecolor('#cccccc')
                spine.set_linewidth(1.5)
        
        # Adjust layout
        plt.tight_layout()           
        plt.savefig('plot_total_files_seeds_by_model_side_temperature.pdf',bbox_inches="tight")
                
    def valid_seeds(self, csv):
        ######################################
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)        
                
        # Calculate means grouped by model and temperature
        grouped_df = df.groupby(['model', 'temperature']).agg({
            'total_files': 'mean',
            'total_files_with_invalid_json': 'mean',
            'total_seeds': 'mean',
            'total_duplicate_seeds': 'mean',
            'total_seeds_with_invalid_struct': 'mean'
        }).reset_index()

        # Calculate metrics
        grouped_df['valid_files_mean'] = grouped_df['total_files'] - grouped_df['total_files_with_invalid_json']
        grouped_df['valid_files_percentage'] = (grouped_df['valid_files_mean'] / grouped_df['total_files']) * 100
        grouped_df['valid_seeds'] = grouped_df['total_seeds'] - grouped_df['total_duplicate_seeds'] - grouped_df['total_seeds_with_invalid_struct']


        grouped_df['model'] = grouped_df['model'].apply(self.format_model_name)
        models = grouped_df['model'].unique()
        markers = ['+','o', 'D', 's', '^', 'v']  # More distinct markers
        color_palette = sns.color_palette("tab10", len(models))

        # Plot for valid seeds
        plt.figure(figsize=(12, 8))
        ax = plt.gca()

        for model, marker, color in zip(models, markers, color_palette):
            model_data = grouped_df[grouped_df['model'] == model]
            
            # Main line with markers
            plt.plot(model_data['temperature'], 
                    model_data['valid_seeds'], 
                    marker=marker,
                    markersize=12,
                    linewidth=3,
                    color=color,
                    label=model,
                    alpha=0.8)
            
            # Shadow effect
            plt.plot(model_data['temperature'], 
                    model_data['valid_seeds'],
                    color='gray',
                    linewidth=4,
                    alpha=0.2,
                    zorder=-1)

        # Styling
        plt.xlabel('Temperature', fontsize=14, fontweight='bold')
        plt.ylabel('Number of Valid Seeds', fontsize=14, fontweight='bold')
        plt.title('Total Valid Seeds Generated vs Temperature', fontweight='bold', fontsize=16, pad=20)

        # Grid and background
        plt.grid(True, linestyle='--', alpha=0.7)
        ax.set_facecolor('#f8f9fa')
        ax.tick_params(axis='both', which='major', labelsize=12)

        # Enhanced legend - now inside the plot
        legend = plt.legend(
            title="Models",
            title_fontsize=12,
            fontsize=11,
            loc='center right',
            bbox_to_anchor=(1, 0.6),
            frameon=True,
            fancybox=True,
            shadow=True,
            borderpad=1
        )
        legend.get_frame().set_facecolor('white')
        legend.get_frame().set_alpha(0.9)

        # Spines
        for spine in ax.spines.values():
            spine.set_edgecolor('#cccccc')
            spine.set_linewidth(1.5)

        plt.tight_layout()
        plt.savefig('plot_valid_seeds.pdf', bbox_inches='tight', dpi=600)
        plt.close()

    def seed_metrics(self, csv):
        ######################################
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)
                
        # Calculate means grouped by model and temperature
        grouped_df = df.groupby(['model', 'temperature']).agg({
            'total_files': 'mean',
            'total_files_with_invalid_json': 'mean',
            'total_seeds': 'mean',
            'total_duplicate_seeds': 'mean',
            'total_seeds_with_invalid_struct': 'mean'
        }).reset_index()

        # Calculate metrics
        grouped_df['valid_files_mean'] = grouped_df['total_files'] - grouped_df['total_files_with_invalid_json']
        grouped_df['valid_files_percentage'] = (grouped_df['valid_files_mean'] / grouped_df['total_files']) * 100
        grouped_df['valid_seeds'] = grouped_df['total_seeds'] - grouped_df['total_duplicate_seeds'] - grouped_df['total_seeds_with_invalid_struct']

        grouped_df['model'] = grouped_df['model'].apply(self.format_model_name)
        models = grouped_df['model'].unique()
                
        # Get visualization scheme using our function
        model_scheme = get_model_visualization_scheme(models)
            
        # Plot setup
        plt.figure(figsize=(12, 8))
        ax = plt.gca()
        
        # Plot for each model
        for model in models:
            model_data = grouped_df[grouped_df['model'] == model]
            temps = model_data['temperature']
            
            # Get color and marker for this model
            color = model_scheme[model]["color"]
            marker = model_scheme[model]["marker"]
            
            # Solid line for valid seeds
            plt.plot(temps, model_data['valid_seeds'], 
                    color=color, 
                    linestyle='-',
                    linewidth=3,
                    marker=marker,
                    markersize=10,
                    label=f'{model}',
                    zorder=3)
                    
            # Dotted line for total seeds
            plt.plot(temps, model_data['total_seeds'],
                    color=color,
                    linestyle=':',
                    linewidth=2,
                    alpha=0.7,
                    marker=marker,
                    markersize=8,
                    zorder=2)
                    
            # Fill between total and valid to show invalid
            plt.fill_between(temps, 
                            model_data['total_seeds'],
                            model_data['valid_seeds'],
                            color=color,
                            alpha=0.1,
                            zorder=1)
                            
            # Add percentage text for valid seeds
            # for x, y, total, valid in zip(temps, model_data['valid_seeds'], 
            #                             model_data['total_seeds'], model_data['valid_seeds']):
            #     percentage = (valid / total * 100) if total > 0 else 0
            #     plt.text(x, y - (total * 0.05),  # Position below the point
            #             f'{percentage:.1f}%',
            #             ha='center',
            #             va='top',
            #             fontsize=8,
            #             color=color,
            #             alpha=0.8)

        # Styling
        plt.xlabel('Temperature', fontsize=14, fontweight='bold')
        plt.ylabel('Number of Seeds', fontsize=14, fontweight='bold')
        plt.title('Seed Generation Quality by Model', fontweight='bold', fontsize=16, pad=20)

        # Grid and background
        plt.grid(True, linestyle='--', alpha=0.3)
        ax.set_facecolor('#f8f9fa')
        ax.tick_params(axis='both', which='major', labelsize=12)

        # Legend inside the plot
        legend = plt.legend(
            title="Models",
            title_fontsize=12,
            fontsize=11,
            loc='center right',
            bbox_to_anchor=(1, 0.6),                        
            frameon=True,
            fancybox=True,
            shadow=True,
            borderpad=1
        )
        legend.get_frame().set_facecolor('white')
        legend.get_frame().set_alpha(0.9)

        # Spines
        for spine in ax.spines.values():
            spine.set_edgecolor('#cccccc')
            spine.set_linewidth(1.5)

        plt.tight_layout()
        plt.savefig('plot_seed_metrics.pdf', bbox_inches='tight', dpi=600)
        plt.close()
                
    def combined_plots(self, csv):
        ######################################
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)
                
        # Calculate means grouped by model and temperature
        grouped_df = df.groupby(['model', 'temperature']).agg({
            'total_files': 'mean',
            'total_files_with_invalid_json': 'mean',
            'total_seeds': 'mean',
            'total_duplicate_seeds': 'mean',
            'total_seeds_with_invalid_struct': 'mean'
        }).reset_index()

        # Calculate metrics
        grouped_df['valid_files_mean'] = grouped_df['total_files'] - grouped_df['total_files_with_invalid_json']
        grouped_df['valid_files_percentage'] = (grouped_df['valid_files_mean'] / grouped_df['total_files']) * 100
        grouped_df['valid_seeds'] = grouped_df['total_seeds'] - grouped_df['total_duplicate_seeds'] - grouped_df['total_seeds_with_invalid_struct']

        grouped_df['model'] = grouped_df['model'].apply(self.format_model_name)
        models = grouped_df['model'].unique()        

        # Create side-by-side plots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
        
        # Get visualization scheme using our function
        model_scheme = get_model_visualization_scheme(models)
                
        # Plot 1: Duplicate Seeds
        for model in models:
            model_data = grouped_df[grouped_df['model'] == model]
            
            # Get color and marker for this model
            color = model_scheme[model]["color"]
            marker = model_scheme[model]["marker"]
            
            ax1.plot(model_data['temperature'], 
                    model_data['total_duplicate_seeds'], 
                    marker=marker,
                    markersize=12,
                    linewidth=3,
                    color=color,
                    label=model,
                    alpha=0.8)
            
            ax1.plot(model_data['temperature'], 
                    model_data['total_duplicate_seeds'],
                    color='gray',
                    linewidth=4,
                    alpha=0.2,
                    zorder=-1)

        ax1.set_xlabel('Temperature', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Number of Duplicate Seeds', fontsize=14, fontweight='bold')
        ax1.set_title('Duplicate Seeds Generated vs Temperature', fontweight='bold', fontsize=16, pad=20)
        ax1.grid(True, linestyle='--', alpha=0.7)
        ax1.set_facecolor('#f8f9fa')
        ax1.tick_params(axis='both', which='major', labelsize=12)

        # Plot 2: combined_plots.pdf
        for model in models:
            model_data = grouped_df[grouped_df['model'] == model]
            
            # Get color and marker for this model
            color = model_scheme[model]["color"]
            marker = model_scheme[model]["marker"]
            
            ax2.plot(model_data['temperature'], 
                    model_data['total_seeds_with_invalid_struct'], 
                    marker=marker,
                    markersize=12,
                    linewidth=3,
                    color=color,
                    label=model,
                    alpha=0.8)
            
            ax2.plot(model_data['temperature'], 
                    model_data['total_seeds_with_invalid_struct'],
                    color='gray',
                    linewidth=4,
                    alpha=0.2,
                    zorder=-1)

        ax2.set_xlabel('Temperature', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Number of Invalid Structure Seeds', fontsize=14, fontweight='bold')
        ax2.set_title('Seeds with Invalid Structure vs Temperature', fontweight='bold', fontsize=16, pad=20)
        ax2.grid(True, linestyle='--', alpha=0.7)
        ax2.set_facecolor('#f8f9fa')
        ax2.tick_params(axis='both', which='major', labelsize=12)

        # Add separate legends for each plot
        for ax in [ax1, ax2]:
            legend = ax.legend(
                title="Models",
                title_fontsize=12,
                fontsize=11,
                loc='best',
                frameon=True,
                fancybox=True,
                shadow=True,
                borderpad=1
            )
            legend.get_frame().set_facecolor('white')
            legend.get_frame().set_alpha(0.9)

        # Style spines for both plots
        for ax in [ax1, ax2]:
            for spine in ax.spines.values():
                spine.set_edgecolor('#cccccc')
                spine.set_linewidth(1.5)

        plt.tight_layout()
        plt.savefig('combined_plots.pdf', bbox_inches='tight', dpi=600)
        plt.close()

    def valid_files_percentage(self, csv):
        ######################################
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)
                
        # Calculate means grouped by model and temperature
        grouped_df = df.groupby(['model', 'temperature']).agg({
            'total_files': 'mean',
            'total_files_with_invalid_json': 'mean',
            'total_seeds': 'mean',
            'total_duplicate_seeds': 'mean',
            'total_seeds_with_invalid_struct': 'mean'
        }).reset_index()

        # Calculate metrics
        grouped_df['valid_files_mean'] = grouped_df['total_files'] - grouped_df['total_files_with_invalid_json']
        grouped_df['valid_files_percentage'] = (grouped_df['valid_files_mean'] / grouped_df['total_files']) * 100
        grouped_df['valid_seeds'] = grouped_df['total_seeds'] - grouped_df['total_duplicate_seeds'] - grouped_df['total_seeds_with_invalid_struct']

        grouped_df['model'] = grouped_df['model'].apply(self.format_model_name)
        models = grouped_df['model'].unique()        

        # Create side-by-side plots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
        
        # Get visualization scheme using our function
        model_scheme = get_model_visualization_scheme(models)
                
        # Plot for valid files percentage
        plt.figure(figsize=(12, 8))
        ax = plt.gca()

        for model in models:
            model_data = grouped_df[grouped_df['model'] == model]
            
            # Get color and marker for this model
            color = model_scheme[model]["color"]
            marker = model_scheme[model]["marker"]
            
            plt.plot(model_data['temperature'], 
                    model_data['valid_files_percentage'], 
                    marker=marker,
                    markersize=12,
                    linewidth=3,
                    color=color,
                    label=model,
                    alpha=0.8)
            
            plt.plot(model_data['temperature'], 
                    model_data['valid_files_percentage'],
                    color='gray',
                    linewidth=4,
                    alpha=0.2,
                    zorder=-1)

        plt.xlabel('Temperature', fontsize=14, fontweight='bold')
        plt.ylabel('Percentage of Valid Outputs (%)', fontsize=14, fontweight='bold')
        plt.title('Percentage of Valid Outputs vs Temperature', fontweight='bold', fontsize=16, pad=20)
        plt.grid(True, linestyle='--', alpha=0.7)
        ax.set_facecolor('#f8f9fa')
        ax.tick_params(axis='both', which='major', labelsize=12)

        legend = plt.legend(
            title="Models",
            title_fontsize=12,
            fontsize=11,
            loc='center right',
            #bbox_to_anchor=(0, 1),
            bbox_to_anchor=(1, 0.7),
            frameon=True,
            fancybox=True,
            shadow=True,
            borderpad=1
        )
        legend.get_frame().set_facecolor('white')
        legend.get_frame().set_alpha(0.9)

        for spine in ax.spines.values():
            spine.set_edgecolor('#cccccc')
            spine.set_linewidth(1.5)

        plt.tight_layout()
        plt.savefig('plot_valid_files_percentage.pdf', bbox_inches='tight', dpi=600)
        plt.close()        
        
    def total_seed_and_files(self, csv):
        ######################################
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)
                
        # Calculate means grouped by model and temperature
        grouped_df = df.groupby(['model', 'temperature']).agg({
            'total_files': 'mean',
            'total_files_with_invalid_json': 'mean',
            'total_seeds': 'mean',
            'total_duplicate_seeds': 'mean',
            'total_seeds_with_invalid_struct': 'mean'
        }).reset_index()

        # Calculate metrics
        grouped_df['valid_files_mean'] = grouped_df['total_files'] - grouped_df['total_files_with_invalid_json']
        grouped_df['valid_files_percentage'] = (grouped_df['valid_files_mean'] / grouped_df['total_files']) * 100
        grouped_df['valid_seeds'] = grouped_df['total_seeds'] - grouped_df['total_duplicate_seeds'] - grouped_df['total_seeds_with_invalid_struct']

        grouped_df['model'] = grouped_df['model'].apply(self.format_model_name)
        models = grouped_df['model'].unique()        

        # Create side-by-side plots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
        
        # Get visualization scheme using our function
        model_scheme = get_model_visualization_scheme(models)
                
        # Plot for duplicate seeds
        plt.figure(figsize=(12, 8))
        ax = plt.gca()

        for model in models:
            model_data = grouped_df[grouped_df['model'] == model]
            
            # Get color and marker for this model
            color = model_scheme[model]["color"]
            marker = model_scheme[model]["marker"]
            
            plt.plot(model_data['temperature'], 
                    model_data['total_duplicate_seeds'], 
                    marker=marker,
                    markersize=12,
                    linewidth=3,
                    color=color,
                    label=model,
                    alpha=0.8)
            
            plt.plot(model_data['temperature'], 
                    model_data['total_duplicate_seeds'],
                    color='gray',
                    linewidth=4,
                    alpha=0.2,
                    zorder=-1)

        plt.xlabel('Temperature', fontsize=14, fontweight='bold')
        plt.ylabel('Number of Duplicate Seeds', fontsize=14, fontweight='bold')
        plt.title('Duplicate Seeds Generated vs Temperature', fontweight='bold', fontsize=16, pad=20)
        plt.grid(True, linestyle='--', alpha=0.7)
        ax.set_facecolor('#f8f9fa')
        ax.tick_params(axis='both', which='major', labelsize=12)

        legend = plt.legend(
            title="Models",
            title_fontsize=12,
            fontsize=11,
            loc='best',
            frameon=True,
            fancybox=True,
            shadow=True,
            borderpad=1
        )
        legend.get_frame().set_facecolor('white')
        legend.get_frame().set_alpha(0.9)

        for spine in ax.spines.values():
            spine.set_edgecolor('#cccccc')
            spine.set_linewidth(1.5)

        plt.tight_layout()
        plt.savefig('plot_duplicate_seeds.pdf', bbox_inches='tight', dpi=600)
        plt.close()
        ######################################

        # Plot for invalid structure seeds
        plt.figure(figsize=(12, 8))
        ax = plt.gca()

        for model in models:
            model_data = grouped_df[grouped_df['model'] == model]
            
            # Get color and marker for this model
            color = model_scheme[model]["color"]
            marker = model_scheme[model]["marker"]
            
            plt.plot(model_data['temperature'], 
                    model_data['total_seeds_with_invalid_struct'], 
                    marker=marker,
                    markersize=12,
                    linewidth=3,
                    color=color,
                    label=model,
                    alpha=0.8)
            
            plt.plot(model_data['temperature'], 
                    model_data['total_seeds_with_invalid_struct'],
                    color='gray',
                    linewidth=4,
                    alpha=0.2,
                    zorder=-1)

        plt.xlabel('Temperature', fontsize=14, fontweight='bold')
        plt.ylabel('Number of Invalid Structure Seeds', fontsize=14, fontweight='bold')
        plt.title('Seeds with Invalid Structure vs Temperature', fontweight='bold', fontsize=16, pad=20)
        plt.grid(True, linestyle='--', alpha=0.7)
        ax.set_facecolor('#f8f9fa')
        ax.tick_params(axis='both', which='major', labelsize=12)

        legend = plt.legend(
            title="Models",
            title_fontsize=12,
            fontsize=11,
            loc='best',
            frameon=True,
            fancybox=True,
            shadow=True,
            borderpad=1
        )
        legend.get_frame().set_facecolor('white')
        legend.get_frame().set_alpha(0.9)

        for spine in ax.spines.values():
            spine.set_edgecolor('#cccccc')
            spine.set_linewidth(1.5)

        plt.tight_layout()
        plt.savefig('plot_invalid_structure_seeds.pdf', bbox_inches='tight', dpi=600)
        plt.close()
                            
    def performance_score_all_metrics(self, csv):
        df = self.build_perf_score_seeds_args_funcs(csv)

        # Group by model and temperature
        result = (
            df.groupby(['model', 'temperature'])
            .apply(lambda group: pd.Series({
                'duplicate_percentage': group['duplicate_percentage'].mean(),
                'invalid_struct_percentage': group['invalid_struct_percentage'].mean(),
                'invalid_args_percentage': group['invalid_args_percentage'].mean(),
                'invalid_functions_percentage': group['invalid_functions_percentage'].mean(),
                'performance_score': group['normalized_performance_score'].mean(),
                'mean_valid_seeds': round(group['valid_seeds'].mean()),
                'mean_total_seeds': round(group['total_seeds'].mean()),
                'mean_valid_args': round((group['total_args_in_seeds'] - group['total_invalid_args_in_seeds']).mean()),
                'mean_valid_functions': round((group['total_functions_in_seeds'] - group['total_invalid_function_in_seeds']).mean())
            }))
            .reset_index()            
        )        

        # Group by model only
        result_model = (
            df.groupby(['model'])            
            .apply(lambda group: pd.Series({
                'duplicate_percentage': group['duplicate_percentage'].mean(),
                'invalid_struct_percentage': group['invalid_struct_percentage'].mean(),
                'invalid_args_percentage': group['invalid_args_percentage'].mean(),
                'invalid_functions_percentage': group['invalid_functions_percentage'].mean(),
                'performance_score': group['normalized_performance_score'].mean(),
                'mean_valid_seeds': round(group['valid_seeds'].mean()),
                'mean_total_seeds': round(group['total_seeds'].mean()),
                'mean_valid_args': round((group['total_args_in_seeds'] - group['total_invalid_args_in_seeds']).mean()),
                'mean_valid_functions': round((group['total_functions_in_seeds'] - group['total_invalid_function_in_seeds']).mean())
            }))
            .reset_index()            
        )        

        # Calculate unique percentage
        result['uniq_percentage'] = 100 - result["duplicate_percentage"]
        result_model['uniq_percentage'] = 100 - result_model["duplicate_percentage"]        

        # Sort by performance score
        result = result.sort_values(by=['performance_score'], ascending=False)
        print(result) 
        
    def performance_score_print_tables(self, csv):
        df = self.build_perf_score_seeds(csv)
        #df = self.build_perf_score_seeds_args_funcs(csv)        
        
        result = (
            df.groupby(['model', 'temperature'])
            .apply(lambda group: pd.Series({
                'duplicate_percentage': group['duplicate_percentage'].mean(),
                'invalid_struct_percentage': group['invalid_struct_percentage'].mean(),                
                'performance_score': group['normalized_performance_score'].mean(),
                'mean_valid_seeds': round(group['valid_seeds'].mean()),
                'mean_total_seeds': round(group['total_seeds'].mean())                
            }))
            .reset_index()            
        )        

        result_model = (
            df.groupby(['model'])            
            .apply(lambda group: pd.Series({
                'duplicate_percentage': group['duplicate_percentage'].mean(),
                'invalid_struct_percentage': group['invalid_struct_percentage'].mean(),                                
                'performance_score': group['normalized_performance_score'].mean(),
                'mean_valid_seeds': round(group['valid_seeds'].mean()),
                'mean_total_seeds': round(group['total_seeds'].mean())                                
            }))
            .reset_index()            
        )        
        
        result['uniq_percentage'] = 100 - result["duplicate_percentage"]
        result_model['uniq_percentage'] = 100 - result["duplicate_percentage"]        
        
        result = result.sort_values(by=['performance_score'], ascending=False)
        print(result)
        
        print("================================================================================================")
        
        result_model= result_model.sort_values(by=['performance_score'], ascending=False)
        print(result_model)
        
        print("================================================================================================")
        
        latex_table = result_model.to_latex(index=False)
        print(latex_table)
        print("================================================================================================") 
                
    def duplicate_cluster_quality_heat(self, csv):
        df = self.build_perf_score_seeds_args_funcs(csv)
        #df = self.build_perf_score_seeds_args_funcs_2(csv)
        #df = self.build_perf_score_seeds(csv)

        # Aggregate data by model and temperature
        result = (
            df.groupby(['model', 'temperature'])
            .apply(lambda group: pd.Series({
                'performance_score': group['normalized_performance_score'].mean()
            }))
            .reset_index()
        )

        # Calculate the mean performance score for each model
        model_performance = result.groupby('model')['performance_score'].mean().reset_index()

        # Sort the models based on the mean performance score in descending order
        sorted_models = model_performance.sort_values(by='performance_score', ascending=False)['model']

        # Reorder the result DataFrame based on the sorted models
        result['model'] = pd.Categorical(result['model'], categories=sorted_models, ordered=True)

        # Pivot the data to create a matrix where rows are models and columns are temperatures
        heatmap_data = result.pivot(index='model', columns='temperature', values='performance_score')

        # Create a heatmap with Reds colormap
        plt.figure(figsize=(14, 8))

        # Use Seaborn's heatmap function with Reds colormap
        sns.heatmap(heatmap_data, annot=True, cmap='YlOrRd', fmt='.1f', linewidths=0.9)

        # Customize the plot
        plt.title('Seed Performance Score per Model and Temperature', fontsize=16)
        plt.xlabel('Temperature', fontsize=14)
        plt.ylabel('Model', fontsize=14)

        # Make y-axis labels horizontal and increase font size
        plt.yticks(rotation=0, fontsize=12)  # Set horizontal y labels with bigger font size

        # Show the plot
        plt.tight_layout()

        plt.savefig('performance_score_model_temp_heatmap.pdf', bbox_inches="tight")      
                  
    def metrics_info(self, csv):
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)
        
        grouped = (
            # Group by model
            df.groupby(['model'])            
            .apply(lambda group: pd.Series({
                'mean_seeds': group['total_seeds'].mean(),
                # 'mean_duplicate_seeds': group['total_duplicate_seeds'].mean(),
                # 'mean_seeds_with_invalid_struct': group['total_seeds_with_invalid_struct'].mean(),
                'mean_invalid_args_in_seeds_percentage': (group['total_invalid_args_in_seeds'].mean() / group['total_args_in_seeds'].mean() * 100) ,
                'mean_invalid_function_in_seeds_percentage': (group['total_invalid_function_in_seeds'].mean() / group['total_functions_in_seeds'].mean() * 100) ,
            }))
            .reset_index()
        )
                
        grouped = grouped.sort_values(by=['mean_invalid_function_in_seeds_percentage', 'mean_invalid_args_in_seeds_percentage'], ascending=False)
        pd.set_option('display.max_columns', None)  # Show all columns
        pd.set_option('display.width', 1000)       # Increase display width for better formatting

        # Print the result
        print(grouped)
         
    def valid(self, csv):
        df = pd.read_csv(csv, header=None, names=self.METRICS_HEADER)

        # Find the global maximum value of total_seeds
        max_total_seeds = df['total_seeds'].max()
        max_total_args_in_seeds = df['total_args_in_seeds'].max()
        max_total_functions_in_seeds = df['total_functions_in_seeds'].max()
        
        df['invalid_args_in_seeds'] = (df['total_invalid_args_in_seeds'] / max_total_args_in_seeds) * 100
        df['invalid_functions_in_seeds'] = (df['total_invalid_function_in_seeds'] / max_total_functions_in_seeds) * 100

        result = (
            #df.groupby(['model', 'temperature'])
            df.groupby(['model'])            
            .apply(lambda group: pd.Series({
                'invalid_args_in_seeds': group['invalid_args_in_seeds'].mean(),
                'invalid_functions_in_seeds': group['invalid_functions_in_seeds'].mean(),
            }))
            .reset_index()            
        )        
        
        result = result.sort_values(by=['model'], ascending=False)
        print(result)

    def coverage_means(self, coverage, metrics):

        df, total_valid_seeds = self.build_coverage_data(coverage)
        total_valid_seeds['model'] = total_valid_seeds['model'].apply(self.format_model_name)
        df['model'] = df['model'].apply(self.format_model_name)   
             
        
        df['instruction_coverage'] = (
            df['coveredInstructions'].div(df['totalInstructions'])
            .mul(100)
            .round(2)
        )

        df['edge_coverage'] = (
            df['coveredEdges'].div(df['totalEdges'])
            .mul(100)
            .round(2)
        )

        coverage_by_model_temp = (
            df.groupby(['model', 'temperature'])
            .agg({
                'instruction_coverage': 'mean',
                'edge_coverage': 'mean'
            })
            .round(2)
            .reset_index()
            .rename(columns={
                'instruction_coverage': 'mean_instruction_coverage_percentage',
                'edge_coverage': 'mean_edge_coverage_percentage'
            })
            .sort_values(['mean_instruction_coverage_percentage', 'mean_edge_coverage_percentage'], ascending=False)
        )

        coverage_by_model_temp = coverage_by_model_temp.merge(total_valid_seeds, on=['model', 'temperature'])
        valid_seed = self.get_mean_valid_seeds_per_model(metrics)
        coverage_by_model_temp = coverage_by_model_temp.merge(valid_seed, on=['model', 'temperature'])
        print(coverage_by_model_temp)

        coverage_by_model= (
            coverage_by_model_temp.groupby(['model'])
            .agg({
                'mean_instruction_coverage_percentage': 'mean',
                'mean_edge_coverage_percentage': 'mean',
                'mean_valid_seeds': 'mean',
                'seed_count': 'mean'
                
            })
            .round(2)
            .reset_index()
            .sort_values(['mean_instruction_coverage_percentage', 'mean_edge_coverage_percentage'], ascending=False)
        )
        print(coverage_by_model)
        
        model_order = coverage_by_model['model'].tolist()
        
        # Plot 1: Coverage Percentage by Model
        plt.figure(figsize=(14, 8))
        ax1 = plt.subplot(2, 2, 1)
        
        model_graph = coverage_by_model.copy()  # Create a copy to avoid modifying original
        model_graph.rename(columns={'mean_instruction_coverage_percentage': 'instruction_coverage'}, inplace=True)        
        model_graph.rename(columns={'mean_edge_coverage_percentage': 'edge_coverage'}, inplace=True)
        model_graph.drop(columns=['mean_valid_seeds', 'seed_count']).set_index('model').plot(kind='bar', ax=ax1)
        plt.title('Average Coverage by Model')
        plt.xlabel('')
        plt.ylim(0, 100)                
        plt.ylabel('Coverage Percentage')
        plt.xticks(rotation=45)
        plt.legend(title='Coverage Metric')
        
        for p in ax1.patches:
            ax1.annotate(f'{p.get_height():.2f}%', 
                        (p.get_x() + p.get_width() / 2., p.get_height()), 
                        ha='center', va='center', 
                        fontsize=8, color='black', 
                        xytext=(0, 13), textcoords='offset points',
                        rotation=50)
        plt.tight_layout()            
        plt.savefig('coverage_means.pdf', bbox_inches="tight")
        
        # Plot 2: Temperature Heatmap Instruction
        plt.figure(figsize=(14, 8))
        ax2 = plt.subplot(2, 2, 1)
        
        pivot_data = coverage_by_model_temp.pivot_table(
            values='mean_instruction_coverage_percentage',
            index='model',
            columns='temperature',
            aggfunc='mean'
        )
        pivot_data = pivot_data.reindex(model_order)
        
        sns.heatmap(pivot_data, annot=True, fmt='.1f', cmap='YlOrRd', ax=ax2, vmax=100)
        plt.title('Instruction Coverage Heatmap (Model vs Temperature)')
        plt.xlabel('Temperature')
        plt.ylabel('Model')
        plt.tight_layout()            
        plt.savefig('instruction_heatmap_mode_temp.pdf', bbox_inches="tight")        

        # Plot 3: Temperature Heatmap Edge
        plt.figure(figsize=(14, 8))
        ax2 = plt.subplot(2, 2, 1)
        
        pivot_data = coverage_by_model_temp.pivot_table(
            values='mean_edge_coverage_percentage',
            index='model',
            columns='temperature',
            aggfunc='mean'
        )
        pivot_data = pivot_data.reindex(model_order)
        
        sns.heatmap(pivot_data, annot=True, fmt='.1f', cmap='Purples', ax=ax2, vmax=100)
        plt.title('Edge Coverage Heatmap (Model vs Temperature)')
        plt.xlabel('Temperature')
        plt.ylabel('Model')
        plt.tight_layout()            
        plt.savefig('edge_heatmap_mode_temp.pdf', bbox_inches="tight")        
        
        # Plot 4: Temperature Heatmap defusechain
        plt.figure(figsize=(14, 8))
        ax2 = plt.subplot(2, 2, 1)        
        defuse_by_model_temp = df.pivot_table(
            values='coveredDefUseChains',
            index='model',
            columns='temperature',
            aggfunc='sum'
        )
        defuse_by_model_temp = defuse_by_model_temp.reindex(model_order)
        
        sns.heatmap(defuse_by_model_temp, annot=True, fmt='.0f', cmap='Greens', ax=ax2)
        plt.title('Total Coverage of DefUse Chain Found (Model vs Temperature)')
        plt.xlabel('Temperature')
        plt.ylabel('Model')
        plt.tight_layout()            
        plt.savefig('defuse_heatmap_mode_temp.pdf', bbox_inches="tight")        
        
        # Plot 5: Temperature Heatmap bugsfound        
        plt.figure(figsize=(14, 8))
        ax2 = plt.subplot(2, 2, 1)        
        bugs_by_model_temp = df.pivot_table(
            values='bugsFound',
            index='model',
            columns='temperature',
            aggfunc='sum'
        )
        bugs_by_model_temp = bugs_by_model_temp.reindex(model_order)
        
        sns.heatmap(bugs_by_model_temp, annot=True, fmt='.0f', cmap="Purples", ax=ax2)
        plt.title('Total Bugs Found (Model vs Temperature)')
        plt.xlabel('Temperature')
        plt.ylabel('Model')
        plt.tight_layout()            
        plt.savefig('bugs_heatmap_mode_temp.pdf', bbox_inches="tight")        
        
        # Plot 6: Coverage Distribution by Model
        plt.figure(figsize=(14, 8))
        ax2 = plt.subplot(2, 2, 1)        
        
        # Create a copy of the dataframe and ensure correct column name
        plot_df = df.copy()
        if 'instruction_coverage' not in plot_df.columns:
            plot_df['instruction_coverage'] = plot_df['mean_instruction_coverage_percentage']
        
        # Use order parameter in violinplot with the processed dataframe
        sns.violinplot(data=plot_df, x='model', y='instruction_coverage', ax=ax2, order=model_order)
        plt.title('Instruction Coverage Distribution by Model')
        plt.xticks(rotation=45)
        plt.xlabel('')
        plt.ylabel('Coverage Percentage')
        plt.tight_layout()            
        plt.savefig('violin_inst_cov.pdf', bbox_inches="tight")
               
    def coverage(self, csv):
        b1_csv = self.load_coverage_data("B1-ins.csv")
        total_instructions = int(b1_csv['totalInstructions'].sum())
        total_edges = b1_csv['totalEdges'].sum()

        df = pd.read_csv(csv, header=None, names=self.COVERAGE_HEADER)
        
        total_grp = df.groupby(['model', 'temperature', 'contract']).size().reset_index(name='row_count')
        print(total_grp.groupby(['model', 'temperature']).size().reset_index(name='seed_count').sort_values(by=['seed_count'], ascending=False))
    
        average_covered_instructions = df.groupby(['model', 'temperature', 'contract'])['coveredInstructions'].mean().reset_index()
        total_inst_grouped = average_covered_instructions.groupby(['model', 'temperature'])['coveredInstructions'].sum().reset_index()
        total_inst_grouped.rename(columns={'coveredInstructions': 'totalCoveredInstructions'}, inplace=True)
        total_inst_grouped['totalCoveredInstructions_percentage'] = (total_inst_grouped['totalCoveredInstructions'] / total_instructions) * 100            
        total_inst_grouped = total_inst_grouped.sort_values(by=['totalCoveredInstructions_percentage'], ascending=False)
        print(total_inst_grouped)
        
        average_covered_edges = df.groupby(['model', 'temperature', 'contract'])['coveredEdges'].mean().reset_index()
        total_edges_grouped = average_covered_edges.groupby(['model', 'temperature'])['coveredEdges'].sum().reset_index()
        total_edges_grouped.rename(columns={'coveredEdges': 'totalCoveredEdges'}, inplace=True)
        total_edges_grouped['totalCoveredEdges_percentage'] = (total_edges_grouped['totalCoveredEdges'] / total_edges) * 100            
        total_edges_grouped = total_edges_grouped.sort_values(by=['totalCoveredEdges_percentage'], ascending=False)
        print(total_edges_grouped)
                
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

        #total_fail = df.groupby(['model'])['deployFailCount'].mean().reset_index()
        total_fail = df.groupby(['model']).size().reset_index()
        print(total_fail)
        # total_fail.rename(columns={'deployFailCount': 'totaldeployFailCount'}, inplace=True)
        # total_fail = total_fail.sort_values(by=['totaldeployFailCount'], ascending=False)
        # print(total_fail)


        total_seeds_per_model = df.groupby('model')['seed_file'].count()
        print(total_seeds_per_model)
        # Find the model with the most seeds
        max_seeds = total_seeds_per_model.max()

        # Normalize the data based on the model with the most seeds
        df['normalizedCoveredEdges'] = df['coveredEdges'] / max_seeds
        df['normalizedCoveredInstructions'] = df['coveredInstructions'] / max_seeds
        df['normalizedBugsFound'] = df['bugsFound'] / max_seeds

        pd.set_option('display.max_columns', None)  # Show all columns
        pd.set_option('display.width', 1000)       # Increase display width for better formatting

        # Group by 'model' and calculate statistics for each model
        model_stats = df.groupby('model').agg({
            # 'normalizedCoveredEdges': ['mean', 'sum', 'std'],
            # 'normalizedCoveredInstructions': ['mean', 'sum', 'std'],
            # 'normalizedBugsFound': ['mean', 'sum', 'std'],
            'coveredEdges': ['mean', 'sum', 'std'],
            'coveredInstructions': ['mean', 'sum', 'std'],
            'bugsFound': ['mean', 'sum', 'std']
        }).reset_index()

        # Display the statistics for each model
        print(model_stats)
        
        
        # Filter rows where any coverage field has a non-zero value
        df_filtered = df[(df['coveredEdges'] > 0) | (df['coveredInstructions'] > 0) | (df['coveredDefUseChains'] > 0)]

        # Count the number of unique contracts for each model
        contracts_with_coverage = df_filtered.groupby('model')['contract'].nunique().sort_values(ascending=False)

        # Print the sorted list of models with the highest number of contracts with coverage
        print(contracts_with_coverage)        
        
        print("========================================")
        print("Model with most coveredEdges by contract")
        
        # Filter rows where coverage fields are greater than zero
        df_filtered = df[(df['coveredEdges'] > 0) | (df['coveredInstructions'] > 0) | (df['coveredDefUseChains'] > 0)]

        # Group by contract and find the best model based on coveredEdges
        best_models = df_filtered.groupby('contract').apply(
            lambda group: group.loc[group['coveredEdges'].idxmax()]
        )

        # Select only the relevant columns for the output (contract, best model, and coverage)
        best_models = best_models[['contract', 'model', 'coveredEdges']]

        # Sort by coveredEdges to display the best models first
        best_models = best_models.sort_values(by='coveredEdges', ascending=False)

        # Print the list of best models for each contract
        #print(best_models)        
        
        wins_count = best_models['model'].value_counts()

        # Sort by number of wins (descending order)
        wins_count = wins_count.sort_values(ascending=False)        
        print(wins_count)                


        print("========================================")
        print("Model with most mean coveredEdges by contract")
        
        # Filter rows where coverage fields are greater than zero
        df_filtered = df[(df['coveredEdges'] > 0) | (df['coveredInstructions'] > 0) | (df['coveredDefUseChains'] > 0)]

        # Group by contract and model, and calculate the mean coveredEdges for each group
        mean_coverage = df_filtered.groupby(['contract', 'model']).agg(
            mean_coveredEdges=('coveredEdges', 'mean'),
            mean_coveredInstructions=('coveredInstructions', 'mean'),
            mean_coveredDefUseChains=('coveredDefUseChains', 'mean')
        ).reset_index()

        # For each contract, find the model with the highest mean coveredEdges
        best_models = mean_coverage.loc[mean_coverage.groupby('contract')['mean_coveredEdges'].idxmax()]

        # Count the number of wins (i.e., the number of times a model is the best for a contract)
        wins_count = best_models['model'].value_counts()

        # Sort by number of wins (descending order)
        wins_count = wins_count.sort_values(ascending=False)

        # Print the sorted list of models by number of wins
        print(wins_count)                
        
        print("========================================")
        print("Model with most coveredInstructions by contract")
        
        # Filter rows where coverage fields are greater than zero
        df_filtered = df[(df['coveredEdges'] > 0) | (df['coveredInstructions'] > 0) | (df['coveredDefUseChains'] > 0)]

        # Group by contract and find the best model based on coveredEdges
        best_models = df_filtered.groupby('contract').apply(
            lambda group: group.loc[group['coveredInstructions'].idxmax()]
        )

        # Select only the relevant columns for the output (contract, best model, and coverage)
        best_models = best_models[['contract', 'model', 'coveredInstructions']]

        # Sort by coveredEdges to display the best models first
        best_models = best_models.sort_values(by='coveredInstructions', ascending=False)

        # Print the list of best models for each contract
        #print(best_models)        
        
        wins_count = best_models['model'].value_counts()

        # Sort by number of wins (descending order)
        wins_count = wins_count.sort_values(ascending=False)        
        print(wins_count)                

        print("========================================")        
        print("Model with mean most coveredInstructions by contract")        
        # Filter rows where coverage fields are greater than zero
        df_filtered = df[(df['coveredEdges'] > 0) | (df['coveredInstructions'] > 0) | (df['coveredDefUseChains'] > 0)]

        # Group by contract and model, and calculate the mean coveredEdges for each group
        mean_coverage = df_filtered.groupby(['contract', 'model']).agg(
            mean_coveredEdges=('coveredEdges', 'mean'),
            mean_coveredInstructions=('coveredInstructions', 'mean'),
            mean_coveredDefUseChains=('coveredDefUseChains', 'mean')
        ).reset_index()

        # For each contract, find the model with the highest mean coveredEdges
        best_models = mean_coverage.loc[mean_coverage.groupby('contract')['mean_coveredInstructions'].idxmax()]

        # Count the number of wins (i.e., the number of times a model is the best for a contract)
        wins_count = best_models['model'].value_counts()

        # Sort by number of wins (descending order)
        wins_count = wins_count.sort_values(ascending=False)

        # Print the sorted list of models by number of wins
        print(wins_count)                

        print("========================================")
        print("Model with most coveredDefUseChains by contract")
        
        # Filter rows where coverage fields are greater than zero
        df_filtered = df[(df['coveredEdges'] > 0) | (df['coveredInstructions'] > 0) | (df['coveredDefUseChains'] > 0)]

        # Group by contract and find the best model based on coveredEdges
        best_models = df_filtered.groupby('contract').apply(
            lambda group: group.loc[group['coveredDefUseChains'].idxmax()]
        )

        # Select only the relevant columns for the output (contract, best model, and coverage)
        best_models = best_models[['contract', 'model', 'coveredDefUseChains', 'temperature']]

        # Sort by coveredEdges to display the best models first
        best_models = best_models.sort_values(by='coveredDefUseChains', ascending=False)

        # Print the list of best models for each contract
        print(best_models)        
        
        wins_count = best_models['model'].value_counts()

        # Sort by number of wins (descending order)
        wins_count = wins_count.sort_values(ascending=False)        
        print(wins_count)                
        print("========================================")


        print("========================================")
        print("Model with most bugsFound by contract")
        
        # Filter rows where coverage fields are greater than zero
        df_filtered = df[(df['coveredEdges'] > 0) | (df['coveredInstructions'] > 0) | (df['coveredDefUseChains'] > 0) | (df['bugsFound'] > 0)]

        # Group by contract and find the best model based on coveredEdges
        best_models = df_filtered.groupby('contract').apply(
            lambda group: group.loc[group['bugsFound'].idxmax()]
        )

        # Select only the relevant columns for the output (contract, best model, and coverage)
        best_models = best_models[['contract', 'model', 'bugsFound', 'temperature']]

        # Sort by coveredEdges to display the best models first
        best_models = best_models.sort_values(by='bugsFound', ascending=False)

        # Print the list of best models for each contract
        print(best_models)        
        
        wins_count = best_models['model'].value_counts()

        # Sort by number of wins (descending order)
        wins_count = wins_count.sort_values(ascending=False)        
        print(wins_count)                
        print("========================================")



        print("================THE BEST OF THE BEST========================")
        # Group by temperature and model
        grouped = df.groupby(['temperature', 'model'])

        # Initialize an empty list to store the results
        results = []

        # Iterate through each group
        for (temperature, model), group in grouped:
            # Calculate the mean of coverage metrics for this group
            mean_covered_edges = group['coveredEdges'].mean()
            mean_covered_instructions = group['coveredInstructions'].mean()
            mean_covered_def_use_chains = group['coveredDefUseChains'].mean()
            total_seeds = group['seed_file'].count()

            # Calculate a score for this model-temperature combination
            score = (mean_covered_edges + mean_covered_instructions + mean_covered_def_use_chains) * total_seeds
            results.append({
                'temperature': temperature,
                'model': model,
                'total_seeds': total_seeds,
                'mean_coveredEdges': mean_covered_edges,
                'mean_coveredInstructions': mean_covered_instructions,
                'mean_coveredDefUseChains': mean_covered_def_use_chains,
                'score': score
            })

        # Convert the results to a DataFrame
        results_df = pd.DataFrame(results)
        
        print(results_df.sort_values(by=['score'], ascending=False))
        # Get the best model and temperature combination overall (highest score)
        best_model_temperature = results_df.loc[results_df['score'].idxmax()]

        # Output the best model and temperature
        print(best_model_temperature)        
        print("================THE BEST OF THE BEST========================")        
        
        metrics = ['coveredEdges', 'coveredInstructions', 'coveredDefUseChains']
        print("\nANOVA Results:")
        for metric in metrics:
            # Group data by model for each metric
            groups = [df[df['model'] == model][metric] for model in df['model'].unique()]
            f_stat, p_value = f_oneway(*groups)
            print(f"Metric: {metric}")
            print(f"  F-statistic: {f_stat:.4f}, p-value: {p_value}")
            if p_value < 0.05:
                print("  Result: Statistically significant differences (p < 0.05)")
            else:
                print("  Result: No statistically significant differences (p >= 0.05)")        
        
        merged_df = (
            average_covered_instructions
            .merge(average_covered_edges, on=['model', 'temperature'])
            .merge(average_defusechain, on=['model', 'temperature'])
            .merge(average_bugsfound, on=['model', 'temperature'])
        )        
        plt.figure(figsize=(12, 8))

        for model in merged_df['model'].unique():
            model_data = merged_df[merged_df['model'] == model]

            # Plot each metric as a separate line
            plt.plot(
                model_data['temperature'],
                model_data['averageCoveredInstructions'],
                label=f'{model} - Avg Covered Instructions',
                linestyle='-', marker='o', linewidth=2
            )
            plt.plot(
                model_data['temperature'],
                model_data['averageCoveredEdges'],
                label=f'{model} - Avg Covered Edges',
                linestyle='--', marker='x', linewidth=2
            )
            plt.plot(
                model_data['temperature'],
                model_data['averageCoveredDefUseChains'],
                label=f'{model} - Avg DefUseChains',
                linestyle='-.', marker='s', linewidth=2
            )
            plt.plot(
                model_data['temperature'],
                model_data['averageBugsFound'],
                label=f'{model} - Avg Bugs Found',
                linestyle=':', marker='^', linewidth=2
            )

        # Labels, title, and legend
        plt.xlabel('Temperature', fontsize=14)
        plt.ylabel('Metrics', fontsize=14)
        plt.title('Metrics vs Temperature (Line Plot)', fontsize=16)
        plt.grid(alpha=0.3)
        plt.legend(fontsize=10, loc='upper right', bbox_to_anchor=(1.3, 1))

        # Adjust layout and show plot
        plt.tight_layout()
        plt.savefig('scatter_plot_coverage.png', dpi=300)
