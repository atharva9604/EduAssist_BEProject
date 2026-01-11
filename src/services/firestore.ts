import { db } from "@/lib/firebase";
import { collection, getDoc, addDoc, doc, setDoc, getDocs, serverTimestamp, updateDoc } from "firebase/firestore";

export async function ensureUserProfile(user: {uid:string; displayName?: string|null; email?: string | null; photoURL?:string|null}){
   if (!db) {
     console.warn("Firestore not available - skipping user profile creation");
     return { needsOnBoarding: false };
   }
   const ref = doc(db,"users",user.uid);
   const snap = await getDoc(ref);
   if(!snap.exists){
    await setDoc(ref,{
      uid: user.uid,
      role: "teacher",
      name: user.displayName?? " ",
      email:user.email?? " ",
      photoURL: user.photoURL?? " ",
      departmentId:" ",
      subjects:[],
      createdAt: serverTimestamp(),
      updatedAt:serverTimestamp(),
    });
    return {needsOnBoarding :true};
   }
   return {needsOnBoarding:false};
}

export const getUsers = async () => {
  const querySnapshot = await getDocs(collection(db, "users"));
  return querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
};

export type TeacherProfile = {
  id: string;
  name?: string;
  email?: string;
  photoURL?: string;
  departmentId?: string;
  role?: string;
};
export async function getTeacherProfile(uid: string): Promise<TeacherProfile | null> {
  const ref = doc(db, "users", uid);
  const snap = await getDoc(ref);
  return snap.exists() ? ({ id: snap.id, ...snap.data() } as TeacherProfile) : null;
}


export async function updateTeacherProfile(uid:string,data:{departmentId?: string,subjects?:string[];name?:string;role?:string}){
  const ref = doc(db,"users",uid);
  await updateDoc(ref,{...data,updatedAt:serverTimestamp()});
}

export const addUser = async (data: { name: string; email: string }) => {
  const docRef = await addDoc(collection(db, "users"), data);
  return docRef.id;
};
