import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    CheckmarkCircleRegular,
    BuildingRegular,
    ArrowRightRegular,
    BrainCircuitRegular,
    DocumentTextRegular,
    SettingsRegular,
} from '@fluentui/react-icons';
import { BentoGrid, BentoGridItem } from '../../components/ui/BentoGrid';
import heroIllustration from '../../assets/landing/hero_illustration.png';

// Import generated assets
import bentoMedia from '../../assets/landing/bento_media.png';
import bentoLegal from '../../assets/landing/bento_legal.png';
import bentoMedical from '../../assets/landing/bento_medical.png';
import bentoFinance from '../../assets/landing/bento_finance.png';
import bentoBidding from '../../assets/landing/bento_bidding.png';
import bentoOfficial from '../../assets/landing/bento_official.png';
import capabilityGeneral from '../../assets/landing/capability_general.png';
import capabilityVertical from '../../assets/landing/capability_vertical.png';
import capabilityEnterprise from '../../assets/landing/capability_enterprise.png';


export default function LandingPage() {
    const navigate = useNavigate();

    // Typewriter effect
    const [typewriterText, setTypewriterText] = useState('');
    const [isDeleting, setIsDeleting] = useState(false);
    const [loopNum, setLoopNum] = useState(0);
    const [typingSpeed, setTypingSpeed] = useState(150);

    const docTypes = ["医疗文书", "法律合同", "自媒体文案", "商务标书", "行政公文"];

    useEffect(() => {
        const handleType = () => {
            const i = loopNum % docTypes.length;
            const fullText = docTypes[i];

            setTypewriterText(isDeleting
                ? fullText.substring(0, typewriterText.length - 1)
                : fullText.substring(0, typewriterText.length + 1)
            );

            setTypingSpeed(isDeleting ? 80 : 150);

            if (!isDeleting && typewriterText === fullText) {
                setTimeout(() => setIsDeleting(true), 1500); // Pause at end
            } else if (isDeleting && typewriterText === '') {
                setIsDeleting(false);
                setLoopNum(loopNum + 1);
            }
        };

        const timer = setTimeout(handleType, typingSpeed);
        return () => clearTimeout(timer);
    }, [typewriterText, isDeleting, loopNum, typingSpeed]);

    const handleTryIt = () => {
        navigate('/files');
    };

    // Updated Bento Grid Items with Images
    const items = [
        {
            title: "自媒体创作",
            description: "精准检测敏感词，发布前快速校验，防止平台限流封禁",
            header: <img src={bentoMedia} alt="Media" className="w-full h-full object-cover group-hover/bento:scale-110 transition-transform duration-500" />,
        },
        {
            title: "法律合规",
            description: "内置法规规则，自动识别漏洞歧义，降低纠纷概率",
            header: <img src={bentoLegal} alt="Legal" className="w-full h-full object-cover group-hover/bento:scale-110 transition-transform duration-500" />,
        },
        {
            title: "医疗质控",
            description: "匹配医保审核标准，校验文书规范，避免质控不合格",
            header: <img src={bentoMedical} alt="Medical" className="w-full h-full object-cover group-hover/bento:scale-110 transition-transform duration-500" />,
        },
        {
            title: "财务报销",
            description: "校验票据信息真实性，匹配报销规则，减少财务风险",
            header: <img src={bentoFinance} alt="Finance" className="w-full h-full object-cover group-hover/bento:scale-110 transition-transform duration-500" />,
        },
        {
            title: "招投标",
            description: "检查格式条款，自动识别废标风险，提高中标率",
            header: <img src={bentoBidding} alt="Bidding" className="w-full h-full object-cover group-hover/bento:scale-110 transition-transform duration-500" />,
        },
        {
            title: "公函与通知",
            description: "审核行文规范、措辞严谨性，统一单位对外口径",
            header: <img src={bentoOfficial} alt="Official" className="w-full h-full object-cover group-hover/bento:scale-110 transition-transform duration-500" />,
        },
    ];


    return (
        <div className="min-h-screen bg-background font-sans text-text-primary selection:bg-primary/20">
            {/* Header */}
            <header className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-border">
                <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
                    <div className="flex items-center space-x-2 font-bold text-xl text-primary">
                        <BrainCircuitRegular className="w-8 h-8" />
                        <span>文书审核专家</span>
                    </div>
                    <div className="flex items-center space-x-4">
                        <button onClick={handleTryIt} className="px-5 py-2 text-sm font-medium bg-primary text-white rounded-lg hover:bg-primary-hover transition-colors shadow-sm hover:shadow-md">
                            免费使用
                        </button>
                    </div>
                </div>
            </header>

            {/* Hero Section */}
            <section className="relative pt-32 pb-20 overflow-hidden">
                <div className="max-w-7xl mx-auto px-4 grid lg:grid-cols-2 gap-12 items-center">
                    <div className="space-y-8 animate-slide-up">
                        <div className="inline-flex items-center px-3 py-1 rounded-full bg-blue-50 text-blue-600 text-sm font-medium border border-blue-100">
                            <span className="flex h-2 w-2 rounded-full bg-blue-600 mr-2"></span>
                            AI 驱动的智能审核引擎
                        </div>
                        <h1 className="text-5xl lg:text-6xl font-extrabold tracking-tight leading-tight text-slate-900">
                            让 <span className="text-primary border-b-4 border-blue-200">{typewriterText}</span><br />
                            无懈可击
                        </h1>
                        <p className="text-xl text-text-secondary max-w-lg leading-relaxed">
                            内置多行业规则，支持自定义审核标准。
                            从源头把控质量，降低合规风险，提升工作效率。
                        </p>
                        <div className="flex flex-col sm:flex-row gap-4 pt-4">
                            <button onClick={handleTryIt} className="px-8 py-4 bg-primary text-white rounded-xl font-semibold hover:bg-primary-hover transition-all shadow-lg hover:shadow-primary/25 flex items-center justify-center gap-2 group">
                                免费使用
                                <ArrowRightRegular className="group-hover:translate-x-1 transition-transform" />
                            </button>
                        </div>
                        <div className="flex items-center gap-6 text-sm text-text-muted pt-4">
                            <div className="flex items-center gap-2">
                                <CheckmarkCircleRegular className="text-green-500" /> 内置 20+ 行业规则
                            </div>
                            <div className="flex items-center gap-2">
                                <CheckmarkCircleRegular className="text-green-500" /> 搭载最强基座大模型
                            </div>
                            <div className="flex items-center gap-2">
                                <CheckmarkCircleRegular className="text-green-500" /> 自主学习审核规则
                            </div>
                        </div>
                    </div>
                    {/* Hero Visual */}
                    <div className="relative hidden lg:block animate-fade-in">
                        <div className="absolute inset-0 bg-gradient-to-tr from-blue-100 to-purple-100 rounded-full filter blur-3xl opacity-50 animate-pulse"></div>
                        <img
                            src={heroIllustration}
                            alt="AI Document Review Dashboard"
                            className="relative w-full h-auto drop-shadow-2xl rounded-2xl transform hover:scale-105 transition-transform duration-500"
                        />
                    </div>
                </div>
            </section>

            {/* Pain Points - Bento Grid 3x2 Layout */}
            <section className="py-24 bg-white relative">
                {/* Decorative background elements can go here */}
                <div className="max-w-7xl mx-auto px-4">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl font-bold text-slate-900 mb-4">解决您的核心痛点</h2>
                        <p className="text-text-secondary text-lg max-w-2xl mx-auto">
                            覆盖六大核心场景，解决人工审核效率低、风险大、成本高的问题
                        </p>
                    </div>
                    {/* Explicitly passing className to BentoGrid not strictly needed if BentoGrid handles it, but ensures structure */}
                    <BentoGrid className="grid-cols-1 md:grid-cols-3">
                        {items.map((item, i) => (
                            <BentoGridItem
                                key={i}
                                title={item.title}
                                description={item.description}
                                header={item.header}

                                className="" /* Removed any col-span logic to ensure 1x1 tiles */
                            />
                        ))}
                    </BentoGrid>
                </div>
            </section>

            {/* Product Unique Features (Restored) */}
            <section className="py-24 bg-slate-50">
                <div className="max-w-7xl mx-auto px-4">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl font-bold text-slate-900 mb-4">为什么选择我们？</h2>
                        <p className="text-text-secondary text-lg max-w-2xl mx-auto">独有的 AI 架构，让审核更智能、更精准</p>
                    </div>
                    <div className="grid md:grid-cols-3 gap-8">
                        <FeatureCard
                            title="内置多行业规则"
                            desc="覆盖法律、医疗、招投标等高频行业，规则实时更新。不用自己搭规则，一键切换审核标准，省80%时间。"
                            icon={<SettingsRegular className="w-8 h-8 text-blue-600" />}
                        />
                        <FeatureCard
                            title="零门槛自定义规则"
                            desc="支持文字描述、文档/表格上传，自动生成审核规则。非技术人员也能操作，适配自媒体、医疗等专属需求。"
                            icon={<DocumentTextRegular className="w-8 h-8 text-indigo-600" />}
                        />
                        <FeatureCard
                            title="AI 自学习"
                            desc="人工反馈的「采纳/不采纳/编辑」审核建议，AI 自动解析并升级规则库。审核标准越用越贴合业务。"
                            icon={<BrainCircuitRegular className="w-8 h-8 text-purple-600" />}
                        />
                    </div>
                </div>
            </section>

            {/* Core Capabilities (Redesigned Zig-Zag Light Theme) */}
            <section className="py-24 bg-white text-slate-900 overflow-hidden">
                <div className="max-w-7xl mx-auto px-4 space-y-24">
                    {/* Capability 1 */}
                    <div className="grid lg:grid-cols-2 gap-16 items-center">
                        <div className="order-2 lg:order-1 relative">
                            <div className="absolute -inset-4 bg-blue-100 blur-2xl rounded-full opacity-50"></div>
                            {/* General Capabilities Image */}
                            <div className="relative aspect-video rounded-2xl bg-gradient-to-br from-slate-50 to-white border border-slate-100 flex items-center justify-center overflow-hidden shadow-lg hover:shadow-xl transition-shadow">
                                <img src={capabilityGeneral} alt="General Capabilities" className="w-full h-full object-cover" />
                            </div>
                        </div>
                        <div className="order-1 lg:order-2 space-y-6">
                            <div className="w-12 h-1 bg-blue-500 rounded-full"></div>
                            <h3 className="text-3xl font-bold">通用基础能力</h3>
                            <p className="text-slate-600 text-lg leading-relaxed">
                                从源头把控质量，夯实文书规范基础
                            </p>
                            <ul className="space-y-4">
                                {[
                                    { strong: "敏感词检测", text: "语义级识别，不漏检" },
                                    { strong: "语义语法/错别字检查", text: "纠正语句不通、文字错误" },
                                    { strong: "文件格式检查", text: "统一字体、页码、行距等规范" }
                                ].map((item, i) => (
                                    <li key={i} className="flex gap-3">
                                        <CheckmarkCircleRegular className="w-6 h-6 text-blue-500 shrink-0" />
                                        <span className="text-slate-600 text-lg">
                                            <strong className="text-slate-900">{item.strong}</strong>：{item.text}
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>

                    {/* Capability 2 */}
                    <div className="grid lg:grid-cols-2 gap-16 items-center">
                        <div className="space-y-6">
                            <div className="w-12 h-1 bg-purple-500 rounded-full"></div>
                            <h3 className="text-3xl font-bold">垂直行业能力</h3>
                            <p className="text-slate-600 text-lg leading-relaxed">
                                专懂你的行话，精准匹配业务场景
                            </p>
                            <ul className="space-y-4">
                                {[
                                    { strong: "合同审核", text: "条款合规、风险点提示" },
                                    { strong: "医疗文书审核", text: "医保合规、病历完整性校验" },
                                    { strong: "招投标文件审核", text: "资质匹配、格式合规检查" },
                                    { strong: "财务票据审核", text: "发票真伪、报销规则匹配" }
                                ].map((item, i) => (
                                    <li key={i} className="flex gap-3">
                                        <CheckmarkCircleRegular className="w-6 h-6 text-purple-500 shrink-0" />
                                        <span className="text-slate-600 text-lg">
                                            <strong className="text-slate-900">{item.strong}</strong>：{item.text}
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                        <div className="relative">
                            <div className="absolute -inset-4 bg-purple-100 blur-2xl rounded-full opacity-50"></div>
                            {/* Vertical Capabilities Image */}
                            <div className="relative aspect-video rounded-2xl bg-gradient-to-br from-slate-50 to-white border border-slate-100 flex items-center justify-center overflow-hidden shadow-lg hover:shadow-xl transition-shadow">
                                <img src={capabilityVertical} alt="Vertical Capabilities" className="w-full h-full object-cover" />
                            </div>
                        </div>
                    </div>

                    {/* Capability 3 */}
                    <div className="grid lg:grid-cols-2 gap-16 items-center">
                        <div className="order-2 lg:order-1 relative">
                            <div className="absolute -inset-4 bg-cyan-100 blur-2xl rounded-full opacity-50"></div>
                            {/* Enterprise Capabilities Image */}
                            <div className="relative aspect-video rounded-2xl bg-gradient-to-br from-slate-50 to-white border border-slate-100 flex items-center justify-center overflow-hidden shadow-lg hover:shadow-xl transition-shadow">
                                <img src={capabilityEnterprise} alt="Enterprise Capabilities" className="w-full h-full object-cover" />
                            </div>
                        </div>
                        <div className="order-1 lg:order-2 space-y-6">
                            <div className="w-12 h-1 bg-cyan-500 rounded-full"></div>
                            <h3 className="text-3xl font-bold">企业级进阶能力</h3>
                            <p className="text-slate-600 text-lg leading-relaxed">
                                为组织赋能，构建全流程风控闭环
                            </p>
                            <ul className="space-y-4">
                                {[
                                    { strong: "数据库联动", text: "对接企业内部系统，批量审核文件" },
                                    { strong: "自动审核闭环", text: "审核→预警→整改→复核全流程" },
                                    { strong: "多角色权限", text: "管理员/审核员/普通用户权限分离" },
                                    { strong: "审核报告导出", text: "支持数据可视化，方便复盘" }
                                ].map((item, i) => (
                                    <li key={i} className="flex gap-3">
                                        <CheckmarkCircleRegular className="w-6 h-6 text-cyan-500 shrink-0" />
                                        <span className="text-slate-600 text-lg">
                                            <strong className="text-slate-900">{item.strong}</strong>：{item.text}
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                </div>
            </section>

            {/* Testimonials Marquee */}
            <section className="py-24 border-t border-slate-100 bg-white overflow-hidden">
                <div className="max-w-7xl mx-auto px-4 mb-16">
                    <h2 className="text-3xl font-bold text-center text-slate-900">用户口碑</h2>
                </div>
                <div className="relative w-full">
                    <div className="absolute left-0 top-0 bottom-0 w-32 bg-gradient-to-r from-white to-transparent z-10"></div>
                    <div className="absolute right-0 top-0 bottom-0 w-32 bg-gradient-to-l from-white to-transparent z-10"></div>
                    <div className="flex w-max animate-scroll gap-6 hover:[animation-play-state:paused]">
                        {[...testimonials, ...testimonials].map((item, idx) => (
                            <TestimonialCard
                                key={idx}
                                quote={item.quote}
                                author={item.author}
                                role={item.role}
                                avatar={item.avatar}
                            />
                        ))}
                    </div>
                </div>
            </section>

            {/* CTA Sections - Personal vs Enterprise */}
            <footer className="py-24 bg-slate-900 text-white relative overflow-hidden">
                <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20"></div>
                <div className="max-w-6xl mx-auto px-4 relative z-10">
                    <div className="grid md:grid-cols-2 gap-8 lg:gap-12">
                        {/* Personal/Team Card */}
                        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-10 flex flex-col items-center text-center justify-between hover:border-blue-500/50 transition-colors group">
                            <div>
                                <h3 className="text-3xl font-bold mb-4">个人/团队快速上手</h3>
                                <p className="text-slate-400 text-xl mb-8">
                                    立即开始体验智能审核，提升效率。
                                    <br />无需配置，注册即用。
                                </p>
                            </div>
                            <button onClick={handleTryIt} className="w-full sm:w-auto px-10 py-4 bg-gradient-to-r from-blue-600 to-blue-500 text-white rounded-xl font-bold text-lg hover:shadow-lg hover:shadow-blue-500/30 transition-all transform group-hover:scale-105">
                                免费使用
                            </button>
                        </div>

                        {/* Enterprise Card */}
                        <div className="bg-gradient-to-br from-slate-900 to-slate-800 border border-blue-500/30 rounded-2xl p-10 flex flex-col items-center text-center justify-between relative overflow-hidden hover:border-blue-400/50 transition-colors">
                            <div className="absolute top-0 right-0 p-4 opacity-10">
                                <BuildingRegular className="w-32 h-32" />
                            </div>
                            <div>
                                <h3 className="text-3xl font-bold mb-6">企业级定制服务</h3>
                                <ul className="text-left space-y-4 mb-8 inline-block text-slate-300 text-lg">
                                    <li className="flex items-center gap-3">
                                        <CheckmarkCircleRegular className="w-6 h-6 text-blue-400" />
                                        <span>链接内部数据库 & API 集成</span>
                                    </li>
                                    <li className="flex items-center gap-3">
                                        <CheckmarkCircleRegular className="w-6 h-6 text-blue-400" />
                                        <span>私有化部署 (On-premise)</span>
                                    </li>
                                    <li className="flex items-center gap-3">
                                        <CheckmarkCircleRegular className="w-6 h-6 text-blue-400" />
                                        <span>7x24 小时专属技术支持</span>
                                    </li>
                                </ul>
                            </div>
                            <button 
                                onClick={() => window.open('https://yinyukeji.feishu.cn/share/base/form/shrcnAsdiND251wqNjeQgC5XnDc', '_blank')}
                                className="w-full sm:w-auto px-10 py-4 bg-transparent border border-blue-400 text-blue-100 rounded-xl font-bold text-lg hover:bg-blue-900/30 hover:text-white transition-all"
                            >
                                申请企业版
                            </button>
                        </div>
                    </div>

                    <div className="mt-20 pt-8 border-t border-slate-800 flex flex-col md:flex-row justify-between items-center gap-4 text-base text-slate-500">
                        <div className="flex gap-6">
                            <a href="#" className="hover:text-slate-300 transition-colors">隐私条款</a>
                            <a href="#" className="hover:text-slate-300 transition-colors">服务条款</a>
                            <a href="#" className="hover:text-slate-300 transition-colors">联系我们</a>
                        </div>
                        <div>
                            &copy; {new Date().getFullYear()} 文书审核专家. All Rights Reserved.
                        </div>
                    </div>
                </div>
            </footer>
        </div>
    );
}

const FeatureCard = ({ title, desc, icon }: { title: string, desc: string, icon: React.ReactNode }) => (
    <div className="bg-white p-8 rounded-2xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow group">
        <div className="mb-4 p-3 bg-slate-50 rounded-xl w-fit group-hover:bg-blue-50 transition-colors">{icon}</div>
        <h3 className="text-2xl font-bold text-slate-900 mb-3">{title}</h3>
        <p className="text-text-secondary text-lg leading-relaxed">{desc}</p>
    </div>
);

const TestimonialCard = ({ quote, author, role, avatar }: { quote: string, author: string, role: string, avatar: string }) => (
    <div className="bg-slate-50 p-6 rounded-xl w-[350px] shrink-0 border border-slate-100">
        <div className="flex gap-1 text-yellow-400 mb-4">★★★★★</div>
        <p className="text-slate-700 text-lg italic mb-4 line-clamp-3">"{quote}"</p>
        <div className="flex items-center gap-3">
            <img
                src={avatar}
                alt={author}
                className="w-12 h-12 rounded-full object-cover border-2 border-white shadow-sm"
            />
            <div>
                <p className="text-base font-bold text-slate-900">{author}</p>
                <p className="text-sm text-slate-500">{role}</p>
            </div>
        </div>
    </div>
);

const testimonials = [
    {
        quote: "以前手动查敏感词要半小时，现在一键搞定，再也没被限流！",
        author: "林小姐",
        role: "小红书博主",
        avatar: "https://coresg-normal.trae.ai/api/ide/v1/text_to_image?prompt=A+stylish+young+Chinese+woman+social+media+influencer+style+portrait+square+hd&image_size=square"
    },
    {
        quote: "AI 帮我揪出很多合同漏洞，客户都说我专业度高了。",
        author: "王律师",
        role: "某律所合伙人",
        avatar: "https://coresg-normal.trae.ai/api/ide/v1/text_to_image?prompt=A+professional+Chinese+lawyer+in+a+suit+confident+office+background+square+hd&image_size=square"
    },
    {
        quote: "标书审核快了60%，废标率降80%，中标金额翻一番。",
        author: "张经理",
        role: "某建筑公司 商务经理",
        avatar: "https://coresg-normal.trae.ai/api/ide/v1/text_to_image?prompt=A+middle-aged+Chinese+businessman+construction+industry+manager+professional+square+hd&image_size=square"
    },
    {
        quote: "文书合规率从75%升到98%，医保罚款直接清零。",
        author: "李主任",
        role: "某三甲医院 质控科",
        avatar: "https://coresg-normal.trae.ai/api/ide/v1/text_to_image?prompt=A+Chinese+doctor+in+a+white+coat+hospital+setting+professional+square+hd&image_size=square"
    },
    {
        quote: "财务报销审核效率提升了3倍，再也不用加班对票据了。",
        author: "刘经理",
        role: "某科技公司 财务",
        avatar: "https://coresg-normal.trae.ai/api/ide/v1/text_to_image?prompt=A+professional+Chinese+woman+office+setting+financial+manager+square+hd&image_size=square"
    },
    {
        quote: "对于我们这种跨国业务，多语言合同审核简直是救星。",
        author: "Michael",
        role: "某外贸企业 法务总监",
        avatar: "https://coresg-normal.trae.ai/api/ide/v1/text_to_image?prompt=A+Western+professional+man+business+suit+corporate+background+square+hd&image_size=square"
    },
    {
        quote: "原来总是担心广告法违规，现在发布前扫一下，安心多了。",
        author: "赵总",
        role: "某电商公司 运营部门负责人",
        avatar: "https://coresg-normal.trae.ai/api/ide/v1/text_to_image?prompt=A+energetic+Chinese+entrepreneur+e-commerce+office+setting+square+hd&image_size=square"
    },
    {
        quote: "招标文件里的坑都被识别出来了，避免了巨大的经济损失。",
        author: "孙顾问",
        role: "某工程咨询公司",
        avatar: "https://coresg-normal.trae.ai/api/ide/v1/text_to_image?prompt=An+experienced+Chinese+consultant+professional+and+trustworthy+square+hd&image_size=square"
    }
];
