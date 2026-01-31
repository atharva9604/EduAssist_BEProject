import { initializeApp, getApps } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: "AIzaSyDzluAyJUuHSc6IRdbgJaDKFaoTmxjOBIY",
  authDomain: "eduassist-b5641.firebaseapp.com",
  projectId: "eduassist-b5641",
  storageBucket: "eduassist-b5641.appspot.com",
  messagingSenderId: "703167688009",
  appId: "1:703167688009:web:19c7a0675ae287d9ca7e98",
  measurementId: "G-79BSV4P2Z9"
};

const app = !getApps().length ? initializeApp(firebaseConfig) : getApps()[0];
const analytics = typeof window !== "undefined" ? getAnalytics(app) : null;

export const auth = getAuth(app);
export const db = getFirestore(app);
export { app, analytics };
