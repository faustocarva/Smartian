module Smartian.Options

open Argu
open Utils

type FuzzerCLI =
  | [<AltCommandLine("-p")>] [<Mandatory>] [<Unique>] Program of path: string
  | [<AltCommandLine("-v")>] [<Unique>] Verbose of int
  | [<AltCommandLine("-t")>] [<Mandatory>] [<Unique>] Timelimit of sec: int
  | [<AltCommandLine("-o")>] [<Mandatory>] [<Unique>] OutputDir of path: string
  | [<AltCommandLine("-s")>] [<Unique>] SeedDir of path: string  
  | [<AltCommandLine("-a")>] [<Unique>] ABIFile of path: string
  | [<AltCommandLine("-x")>] [<Unique>] DumpSeed
  | [<Unique>] WithBugGain
  | [<Unique>] NoSDFA  
  | [<Unique>] NoDDFA
  | [<Unique>] UseLLLMSeeds
  | [<Unique>] CheckOptionalBugs
  | [<Unique>] UseOthersOracle
with
  interface IArgParserTemplate with
    member s.Usage =
      match s with
      | Program _ -> "Target program for test case generation with fuzzing."
      | Verbose _ -> "Verbosity level to control debug messages."
      | Timelimit _ -> "Timeout for fuzz testing (in seconds)."
      | OutputDir _ -> "Directory to store testcase outputs."
      | SeedDir _ -> "Directory with LLM seeds."      
      | ABIFile _ -> "ABI JSON file."
      | DumpSeed _ -> "Dump Initial Seeds."      
      | NoSDFA -> "Disable static data-flow analysis to guide fuzzing."
      | WithBugGain -> "Enable the feedback from bugs found."
      | NoDDFA -> "Disable dynamic data-flow analysis during the fuzzing."
      | UseLLLMSeeds -> "Enable the use of LLM inital seeds for fuzzing."      
      | CheckOptionalBugs ->
        "Detect optional bugs (e.g. requirement violation) disabled by default."
      | UseOthersOracle ->
        "Report bugs using other tools' oracles as well.\n\
        Currently we support (BD/IB/ME/RE) X (sFuzz/ILF/Mythril/MANTICORE)."

type FuzzOption = {
  Verbosity         : int
  OutDir            : string
  SeedInDir         : string  
  Timelimit         : int
  ProgPath          : string  
  ABIPath           : string
  DumpSeed          : bool
  WithBugGain       : bool  
  StaticDFA         : bool
  DynamicDFA        : bool
  UseLLLMSeeds      : bool
  CheckOptionalBugs : bool
  UseOthersOracle   : bool
}

let parseFuzzOption (args: string array) =
  let cmdPrefix = "dotnet Smartian.dll fuzz"
  let parser = ArgumentParser.Create<FuzzerCLI> (programName = cmdPrefix)
  let r = try parser.Parse(args) with
          :? Argu.ArguParseException -> printLine (parser.PrintUsage()); exit 1
  { Verbosity = r.GetResult (<@ Verbose @>, defaultValue = 1)
    OutDir = r.GetResult (<@ OutputDir @>)
    SeedInDir = r.GetResult (<@ SeedDir @>, defaultValue = "")    
    Timelimit = r.GetResult (<@ Timelimit @>)
    ProgPath = r.GetResult (<@ Program @>)
    ABIPath = r.GetResult(<@ ABIFile @>, defaultValue = "")
    DumpSeed = (r.Contains(<@ DumpSeed @>))    
    StaticDFA = not (r.Contains(<@ NoSDFA @>))  // Enabled by default.
    DynamicDFA = not (r.Contains(<@ NoDDFA @>)) // Enabled by default.
    UseLLLMSeeds = (r.Contains(<@ UseLLLMSeeds @>))
    WithBugGain = (r.Contains(<@ WithBugGain @>))    
    CheckOptionalBugs = r.Contains(<@ CheckOptionalBugs @>)
    UseOthersOracle = r.Contains(<@ UseOthersOracle @>) }
