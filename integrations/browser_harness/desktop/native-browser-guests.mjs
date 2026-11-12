// Adapted from DeepSeek Harness apps/desktop/src/browser-guests.ts (MIT).
// Native UI, lease checks and sandbox policy retained. Partitions persist by workspace.
import {app,session} from 'electron';
import {randomUUID,createHash} from 'node:crypto';
const DESKTOP_IPC={browserOpenRequested:'friday-native-browser-open'};
export class DesktopBrowserGuests {
	hostUrl;
	partitions = /* @__PURE__ */ new Map();
	leases = /* @__PURE__ */ new Map();
	observers = new Set();
	subscribe(callback) { this.observers.add(callback);return()=>this.observers.delete(callback); }
	notify() { for(const callback of this.observers)callback(); }
	/** @param hostUrl - current authenticated DSH Host, which guests cannot request. */
	constructor(hostUrl) {
		this.hostUrl = hostUrl;
	}
	/**
	* Reserve one guest in a workspace's process-lifetime partition.
	* @param owner - authenticated primary application WebContents.
	* @param workspace - workspace identity received over IPC.
	* @returns opaque lease and the partition approved for it.
	*/
	acquire(owner, workspace) {
		if (typeof workspace !== "string" || workspace.length === 0 || workspace.length > 4096) throw new Error("desktop browser: a workspace storage identity is required");
		let partition = this.partitions.get(workspace);
		if (partition === void 0) {
			partition = `persist:friday-sidebar-browser-${createHash("sha256").update(process.platform === "win32" ? workspace.toLowerCase() : workspace).digest("hex")}`;
			this.configureSession(session.fromPartition(partition));
			this.partitions.set(workspace, partition);
		}
		const lease = randomUUID();
		this.leases.set(lease, {
			owner,
			workspace,
			partition,
			attached: false
		});
		return {
			lease,
			partition
		};
	}
	/**
	* Release only a lease issued to this application window; workspace storage survives.
	* @param owner - authenticated IPC sender.
	* @param id - lease received over IPC.
	*/
	async release(owner, id) {
		if (typeof id !== "string") throw new Error("desktop browser: invalid guest lease");
		const key = id;
		const lease = this.leases.get(key);
		if (lease === void 0) return;
		if (lease.owner !== owner) throw new Error("desktop browser: guest belongs to another window");
		lease.releaseInput?.();
		this.leases.delete(key);
		const guest = lease.guest;
		if (guest !== void 0 && !guest.isDestroyed()) {
			const destroyed = new Promise((resolve) => {
				guest.once("destroyed", resolve);
			});
			guest.close({ waitForBeforeUnload: false });
			await destroyed;
		}
	}
	/**
	* Install attachment checks before the application document can create a webview.
	* @param window - primary application window.
	* @param attachInput - attaches native input after guest ownership is verified and returns its disposer.
	*/
	bind(owner, attachInput = () => () => {}) {
		owner.on("will-attach-webview", (event, preferences, params) => {
			const id = typeof params.src === "string" && params.src.startsWith("about:blank#") ? params.src.slice(12) : "";
			const lease = this.leases.get(id);
			if (lease === void 0 || lease.owner !== owner || lease.attached || params.partition !== lease.partition) {
				event.preventDefault();
				return;
			}
			lease.attached = true;
			for (const key of Object.keys(preferences)) if (key !== "disablePopups") Reflect.deleteProperty(preferences, key);
			Object.assign(preferences, {
				partition: lease.partition,
				nodeIntegration: false,
				nodeIntegrationInWorker: false,
				nodeIntegrationInSubFrames: false,
				contextIsolation: true,
				sandbox: true,
				backgroundThrottling: false,
				webSecurity: true,
				allowRunningInsecureContent: false,
				webviewTag: false,
				plugins: false,
				navigateOnDragDrop: false,
				disableDialogs: true,
				devTools: !app.isPackaged
			});
			params.httpreferrer = "";
		});
		owner.on("did-attach-webview", (_event, guest) => {
			let attachedLease;
			guest.once("dom-ready", () => {
				const url = guest.getURL();
				const id = url.startsWith("about:blank#") ? url.slice(12) : "";
				const lease = this.leases.get(id);
				if (lease === void 0 || lease.owner !== owner || lease.guest !== void 0) {
					guest.close({ waitForBeforeUnload: false });
					return;
				}
				lease.guest = guest;
				attachedLease = id;
				lease.releaseInput = attachInput(guest, id);
				guest.once("destroyed", () => {
					lease.releaseInput?.();
					this.leases.delete(id);
				});
			});
			guest.setWindowOpenHandler(({ url, postBody }) => {
				const lease = attachedLease === void 0 ? void 0 : this.leases.get(attachedLease);
				if (attachedLease !== void 0 && lease?.guest === guest && lease.owner === owner && !owner.isDestroyed() && postBody === void 0 && this.allowedNavigation(url)) {
					const request = {
						lease: attachedLease,
						url: new URL(url).href
					};
					owner.send(DESKTOP_IPC.browserOpenRequested, request);
				}
				return { action: "deny" };
			});
			guest.on("will-frame-navigate", (event) => {
				if (event.isMainFrame && !this.allowedNavigation(event.url)) event.preventDefault();
			});
			guest.on("will-redirect", (event, url, _inPlace, mainFrame) => {
				if (mainFrame && !this.allowedNavigation(url)) event.preventDefault();
			});
			guest.on("will-attach-webview", (event) => {
				event.preventDefault();
			});
			guest.on("login", (event, _details, _authInfo, callback) => {
				event.preventDefault();
				callback();
			});
		});
		const releaseAll = () => {
			for (const [id, lease] of this.leases) if (lease.owner === owner) this.release(owner, id).catch((error) => {
				console.error(error);
			});
		};
		owner.on("did-start-navigation", (_event, _url, inPlace, mainFrame) => {
			if (mainFrame && !inPlace) releaseAll();
		});
		owner.on("render-process-gone", releaseAll);
		owner.once("destroyed", releaseAll);
	}
	async flush() {
    for (const partition of this.partitions.values()) { const profile=session.fromPartition(partition);await profile.cookies.flushStore();profile.flushStorageData(); }
  }
	configureSession(browserSession) {
		browserSession.setPermissionRequestHandler((_contents, _permission, callback) => {
			callback(false);
		});
		browserSession.setPermissionCheckHandler(() => false);
		browserSession.setDevicePermissionHandler(() => false);
		browserSession.setDisplayMediaRequestHandler((_request, callback) => {
			callback({});
		});
		browserSession.on("will-download", (event,item,contents) => {
      const lease=[...this.leases.values()].find(value=>value.guest===contents);
      try { if(lease?.downloadHandler&&this.allowedNavigation(contents.getURL())) { lease.downloadHandler(item);return; } } catch { item?.cancel(); }
			event.preventDefault();
		});
		browserSession.webRequest.onBeforeRequest((details, callback) => {
			const url = new URL(details.url);
			callback({ cancel: [
				"http:",
				"https:",
				"ws:",
				"wss:"
			].includes(url.protocol) ? url.username !== "" || url.password !== "" || this.isApplicationHost(url) : ![
				"about:",
				"data:",
				"blob:"
			].includes(url.protocol) });
		});
	}
	allowedNavigation(value) {
		if (!URL.canParse(value)) return false;
		const url = new URL(value);
		return ["http:", "https:"].includes(url.protocol) && url.username === "" && url.password === "" && !this.isApplicationHost(url);
	}
	isApplicationHost(url) {
		const value = this.hostUrl();
		if (value === void 0) return false;
		const host = new URL(value);
		return url.port === host.port && (url.hostname === host.hostname || [
			"localhost",
			"127.0.0.1",
			"[::1]"
		].includes(url.hostname));
	}
};
