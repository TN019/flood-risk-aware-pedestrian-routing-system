/** Whether the page was opened on this computer or its own network rather than at a public
    address (such as a temporary link from deploy/share.sh): localhost and *.localhost, loopback
    (127.x.x.x, ::1), .local names, and private network addresses (10.x.x.x, 172.16–31.x.x,
    192.168.x.x, and IPv6 fc00::/7 and fe80::/10). Anything else is public. */
export function isLocalHost(hostname: string): boolean {
  // location.hostname keeps the brackets around an IPv6 address; a name may end in a dot.
  const host = hostname.toLowerCase().replace(/^\[(.*)\]$/, "$1").replace(/\.$/, "");
  if (host === "localhost" || host.endsWith(".localhost") || host.endsWith(".local")) return true;

  const v4 = /^(\d{1,3})\.(\d{1,3})\.\d{1,3}\.\d{1,3}$/.exec(host);
  if (v4) {
    const [a, b] = [Number(v4[1]), Number(v4[2])];
    return a === 127 || a === 10 || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168);
  }

  // The first group has all four digits in these ranges (fc00–fdff, fe80–febf).
  if (host.includes(":")) return host === "::1" || /^f[cd][0-9a-f]{2}:/.test(host) || /^fe[89ab][0-9a-f]:/.test(host);
  return false;
}
