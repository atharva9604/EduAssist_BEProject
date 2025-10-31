'use client';

import React from 'react'
import { useRouter } from 'next/navigation';
import { IoIosPaper } from 'react-icons/io'
import { MdAssignment } from 'react-icons/md'
import { PiFilePptBold ,} from 'react-icons/pi'

const TextArea = () => {
  const router = useRouter();

  const handleQuestionPaper = () => {
    router.push('/question-paper');
  };

  const handlePPT = () => {
    router.push('/ppt-generator');
  };

  return (
    <div className='relative'>
        <textarea 
          className='w-200 h-60 p-5 border border-gray-600 rounded-lg bg-gray-800 text-white placeholder-gray-400 focus:border-[#DAA520] focus:outline-none' 
          name="" 
          id="" 
          placeholder='Type what you want to do...'
        />
        <div className='absolute bottom-5 left-2 flex gap-2'>
          <button onClick={handlePPT} className='flex justify-center items-center gap-1 text-xs cursor-pointer bg-[#DAA520] text-black px-2 py-1 rounded hover:bg-[#B8860B] transition'><PiFilePptBold /> PPT</button>
          <button 
            onClick={handleQuestionPaper}
            className='flex justify-center items-center gap-1 text-xs cursor-pointer bg-[#DAA520] text-black px-2 py-1 rounded hover:bg-[#B8860B] transition'>
            <IoIosPaper /> Question Paper
          </button>
          <button className='flex justify-center items-center gap-1 text-xs cursor-pointer bg-[#DAA520] text-black px-2 py-1 rounded hover:bg-[#B8860B] transition'><MdAssignment />Assignments</button>
          
        </div>
    </div>
  )
}

export default TextArea