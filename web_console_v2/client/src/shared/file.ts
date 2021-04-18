export function readAsJSONFromFile<T = object>(file: File): Promise<T> {
  return new Promise((resolve, reject) => {
    if (!window.FileReader) {
      return reject(
        new Error(
          "Detect that Environment doesn't support FileReader yet, please using lastest Chrome",
        ),
      );
    }
    const reader = new FileReader();
    reader.onload = function () {
      try {
        let result = JSON.parse(this.result?.toString()!);
        resolve(result);
      } catch (error) {
        reject(error);
      }
    };
    reader.onerror = reject;
    reader.onabort = reject;

    reader.readAsText(file);
  });
}

export function readAsBinaryStringFromFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = function () {
      if (typeof reader.result === 'string') {
        resolve(btoa(reader.result));
      }
    };
    reader.onerror = reject;
    reader.onabort = reject;
    reader.readAsBinaryString(file);
  });
}
