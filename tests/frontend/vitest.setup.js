import { JSDOM } from "jsdom";
import { createCanvas } from "canvas";

// Initialize JSDOM with a valid URL
const jsdom = new JSDOM("", { url: "http://localhost/" });

// Mock HTMLCanvasElement for DotLottie
global.window = jsdom.window;
global.document = jsdom.window.document;

// Mock HTMLCanvasElement.getContext
global.HTMLCanvasElement.prototype.getContext = function (type) {
    if (type === "2d") {
        return createCanvas(300, 150).getContext("2d");
    }
    return null;
};

// Mock localStorage
Object.defineProperty(global, "localStorage", {
    value: {
        storage: {},
        getItem: function (key) {
            return this.storage[key] || null;
        },
        setItem: function (key, value) {
            this.storage[key] = value;
        },
        removeItem: function (key) {
            delete this.storage[key];
        },
        clear: function () {
            this.storage = {};
        },
    },
    writable: true,
});
