namespace Smartian

open EVMAnalysis
open Nethermind.Core

/// Represents a single argument value, composed of Element array.
type Arg = {
  Spec : ArgSpec
  /// An array of elements.
  Elems : Element array
  /// Specifies the offset within an argument (i.e. the index of 'Elems'), which
  /// will be used for the next grey-box concolic testing.
  ElemCursor : int
}

module Arg =

  let init (argSpec: ArgSpec) =
    let elems =
      match argSpec.Kind with
      // Do not support dimension >= 4 for now.
      | Array (_, Array (_, Array (_, Array _))) -> failwith "Unsupported array"
      | Array (size1, Array (size2, Array (size3, elemTyp))) ->
        let len1 = SizeType.decideLen size1
        let len2 = SizeType.decideLen size2
        let len3 = SizeType.decideLen size3
        let len = len1 * len2 * len3
        Array.init len (fun _ -> Element.init elemTyp)
      // 2-dimensional arrays.
      | Array (size1, Array (size2, elemTyp)) ->
        let len = SizeType.decideLen size1 * SizeType.decideLen size2
        Array.init len (fun _ -> Element.init elemTyp)
      // 1-dimensional arrays.
      | Array (size, elemTyp) ->
        Array.init (SizeType.decideLen size) (fun _ -> Element.init elemTyp)
      // Singleton type.
      | t -> [| Element.init t |]
    { Spec = argSpec; Elems = elems; ElemCursor = 0 }

  //TODO: arrays of bytes
  let private buildArgs len argKind (bytes: obj) =
    match argKind with
    | UInt width | Int width -> 
        match bytes with
        | null -> Array.init len (fun _ -> Element.init argKind)  // Create empty array if null
        | _ -> 
            let numArray = bytes :?> bigint[]
            if numArray.Length = 0 then
                Array.init len (fun _ -> Element.init argKind)  // Create empty array if empty
            else
                numArray |> Array.mapi (fun _ v -> Element.initWithValues argKind v)    
    | Address -> 
        match bytes with
        | null -> Array.init len (fun _ -> Element.init argKind)  // Create empty array if null
        | _ -> 
            let addressArray = bytes :?> Address[]
            if addressArray.Length = 0 then
                Array.init len (fun _ -> Element.init argKind)  // Create empty array if empty
            else
                addressArray |> Array.mapi (fun _ v -> Element.initWithValues argKind v)    
    | Byte -> 
          Array.init len (fun _ -> Element.init argKind)
    | Bool -> 
        (bytes :?> bool[]) |> Array.mapi (fun i v -> Element.initWithValues argKind v)    
    | String -> (bytes :?> string[]) |>  Array.mapi (fun _ v -> Element.initWithValues argKind v)
    | Array _ -> failwithf "Array type not allowed for an element"

  //TODO: only singleton elements and 1-Arrays.
  let initWithValues (argSpec: ArgSpec) value =
    let elems =
      match argSpec.Kind with
      // Do not support dimension >= 4 for now.
      | Array (_, Array (_, Array (_, Array _))) -> failwith "Unsupported array"
      | Array (size1, Array (size2, Array (size3, elemTyp))) ->
        let len1 = SizeType.decideLen size1
        let len2 = SizeType.decideLen size2
        let len3 = SizeType.decideLen size3
        let len = len1 * len2 * len3
        Array.init len (fun _ -> Element.init elemTyp)
      // 2-dimensional arrays.
      | Array (size1, Array (size2, elemTyp)) ->
        let len = SizeType.decideLen size1 * SizeType.decideLen size2
        Array.init len (fun _ -> Element.init elemTyp)
      // 1-dimensional arrays.
      | Array (size, elemTyp) ->
        // let typeInfo = value.GetType()
        // printfn "Type Name INTERNO ARRAY: %s" typeInfo.Name
        // printfn "Value: %A" value
        // printfn "elemTyp: %A" elemTyp        
        buildArgs (SizeType.decideLen size) elemTyp value
      // Singleton type.
      | t -> 
        [| (Element.initWithValues t value)|]
    { Spec = argSpec; Elems = elems; ElemCursor = 0 }


  /// Postprocess to ensure that the value is valid for a constructor argument.
  let fixForConstructor arg =
    let newElems =
      match arg.Spec.Kind with
      // 1-dimensional address arrays.
      | Array (size, Address) ->
        Array.replicate (SizeType.decideLen size) Element.DEPLOYER_ADDR
      // Singleton addres.
      | Address -> [| Element.DEPLOYER_ADDR |]
      | _ -> arg.Elems
    { arg with Elems = newElems }

  /// Return a deep-copied argument of a given argument.
  let copy arg =
    { arg with Arg.Elems = Array.map Element.copy arg.Elems }

  /// Concretize an argument into an array of 'byte array'.
  let concretize arg =
    { ArgSpec = arg.Spec; Bytes = Array.collect Element.concretize arg.Elems }

  /// Get the current element pointed by cursor.
  let getCurElem arg =
    arg.Elems.[arg.ElemCursor]

  /// Update (replace) the current element pointed by cursor.
  let setCurElem arg newElem =
    let newElems = Array.copy arg.Elems
    newElems.[arg.ElemCursor] <- newElem
    { arg with Elems = newElems }

  /// Set the element cursor position of the given argument.
  let setCursor arg newPos =
    { arg with ElemCursor = newPos}

  let rewindByteCursors arg =
    let mapper i elem =
      setCurElem (setCursor arg i) (Element.rewindByteCursor elem)
    Array.mapi mapper arg.Elems
