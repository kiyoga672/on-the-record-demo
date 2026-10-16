import dotenv from 'dotenv';
import path from 'node:path';
dotenv.config({path:path.resolve(process.cwd(),'../../.env')});
/** @type {import('next').NextConfig} */
const config = { poweredByHeader:false, experimental:{cpus:2} };
export default config;
