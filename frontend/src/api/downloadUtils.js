/**
 * Trigger a browser file-save from a Blob received via
 * an authenticated axios request.
 *
 * Downloads are fetched with axios (responseType: "blob")
 * so the JWT is sent in the Authorization header.
 * The JWT is never placed in a URL query parameter.
 */
export function triggerBlobDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  // Revoke after a short delay so the download can begin
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}
