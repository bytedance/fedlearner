export function readJSONFromInput<T>(selectedFile: File): Promise<T> {
  return new Promise((resolve, reject) => {
    if (!window.FileReader) {
      return reject(
        new Error('Detect that FileReader is not supported, please using lastest Chrome'),
      )
    }
    const reader = new FileReader()
    reader.readAsText(selectedFile)

    reader.onload = function () {
      let result = JSON.parse(this.result?.toString()!)
      resolve(result)
    }
    reader.onerror = reject
    reader.onabort = reject
  })
}
