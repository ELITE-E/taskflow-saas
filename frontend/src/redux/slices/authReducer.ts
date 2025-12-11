import {createSlice,PayloadAction} from '@reduxjs/toolkit'
import { Interface } from 'readline'

interface User{
    'id':number,
    'username':string,
    'email':string,
    'first_name':string,
    'last_name':string
}

interface AuthState{
    'user':User|null,
    'isAuthenticated':boolean,
    'loading':boolean,
    'error':string|null
}

const initialState:AuthState={
    'user':null,
    'isAuthenticated':false,
    'loading':true, //Starts scanning for auth token to allow access or not 
    'error':null
}

const authSlice=createSlice({
    /** 
     This slice holds the user data and handles the state transitions (login, logout, pending).
     */
    name:'auth',
    initialState,
    reducers:{
        setLoading(state,action:PayloadAction<boolean>){
            state.loading=action.payload;
        },

        setUser(state,action:PayloadAction<User|null>){
            state.user=action.payload;
            state.isAuthenticated=!!action.payload;
            state.loading=false;
            state.error=null;
        },

        setError(state,action:PayloadAction<string|null>){
            state.error=action.payload;
            state.loading=false
        },

        logout(state) {
      state.user = null;
      state.isAuthenticated = false;
      state.loading = false;
      state.error = null;
    },
    },
})

export const  {setLoading,setUser,setError,logout}=authSlice.actions
export default authSlice.reducer