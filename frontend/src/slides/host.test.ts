import { describe, expect, it } from "vitest";
import { isLocalHost } from "./host";

describe("isLocalHost", () => {
  it("is local for localhost", () => {
    expect(isLocalHost("localhost")).toBe(true);
    expect(isLocalHost("LOCALHOST")).toBe(true);
    expect(isLocalHost("localhost.")).toBe(true);
    expect(isLocalHost("app.localhost")).toBe(true);
  });

  it("is local for loopback addresses", () => {
    expect(isLocalHost("127.0.0.1")).toBe(true);
    expect(isLocalHost("127.1.2.3")).toBe(true);
    expect(isLocalHost("[::1]")).toBe(true);
    expect(isLocalHost("::1")).toBe(true);
  });

  it("is local for .local names", () => {
    expect(isLocalHost("my-laptop.local")).toBe(true);
  });

  it("is local for private network addresses", () => {
    expect(isLocalHost("10.0.0.5")).toBe(true);
    expect(isLocalHost("172.16.0.1")).toBe(true);
    expect(isLocalHost("172.31.255.255")).toBe(true);
    expect(isLocalHost("192.168.1.20")).toBe(true);
    expect(isLocalHost("[fd12:3456::1]")).toBe(true);
    expect(isLocalHost("[fe80::1]")).toBe(true);
  });

  it("is public for anything else", () => {
    expect(isLocalHost("calm-river-stone.trycloudflare.com")).toBe(false);
    expect(isLocalHost("example.com")).toBe(false);
    expect(isLocalHost("lvh.me")).toBe(false);
    expect(isLocalHost("127.0.0.1.nip.io")).toBe(false);
    expect(isLocalHost("localhost.example.com")).toBe(false);
    expect(isLocalHost("8.8.8.8")).toBe(false);
    expect(isLocalHost("11.0.0.1")).toBe(false);
    expect(isLocalHost("172.15.0.1")).toBe(false);
    expect(isLocalHost("172.32.0.1")).toBe(false);
    expect(isLocalHost("192.169.0.1")).toBe(false);
    expect(isLocalHost("[2001:db8::1]")).toBe(false);
    expect(isLocalHost("[fc::1]")).toBe(false);
    expect(isLocalHost("")).toBe(false);
  });
});
