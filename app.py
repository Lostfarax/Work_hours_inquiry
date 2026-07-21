import streamlit as st
import pandas as pd
from datetime import datetime

# 页面配置
st.set_page_config(page_title="员工核对工时系统", page_icon="⏱️", layout="wide")

st.title("⏱️ 员工每日工时核对 Portal")
st.caption("提示：本系统仅用于核对每日工作小时数与项目明细，数据源随 Excel 动态更新。")

# 1. 读取 Excel 数据函数
@st.cache_data(ttl=60)  # 60秒刷新一次数据
def load_data():
    try:
        df = pd.read_excel("工时明细表.xlsx")
        # 确保关键列类型正确
        if "工号" in df.columns:
            df["工号"] = df["工号"].astype(str).str.strip()
        if "Payroll编号" in df.columns:
            df["Payroll编号"] = pd.to_numeric(df["Payroll编号"], errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"无法读取 Excel 文件，请确认根目录下存在 '工时明细表.xlsx'，且包含标准列名。错误信息: {e}")
        return None

df = load_data()

if df is not None:
    # 检验必要的列
    required_cols = ["工号", "日期", "工作小时", "工作项目", "Payroll编号"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        st.warning(f"⚠️ 您的 Excel 文件缺少以下必要列，请先补充列名：{missing_cols}")
        st.info("建议表头格式：[工号] [员工姓名] [日期] [工作小时] [工作项目] [Payroll编号]")
    else:
        # 获取最新（当前）的 Payroll 编号
        latest_payroll = int(df["Payroll编号"].max())
        
        # --- 侧边栏：查询条件 ---
        st.sidebar.header("🔍 工时查询")
        
        # 输入工号
        input_emp_id = st.sidebar.text_input("请输入您的工号：", value="").strip()
        
        # 选择 Payroll 编号（默认选择最新的一期）
        all_payrolls = sorted(df["Payroll编号"].unique(), reverse=True)
        selected_payroll = st.sidebar.selectbox(
            "选择 Payroll 账期编号：", 
            all_payrolls, 
            index=0 if latest_payroll in all_payrolls else 0,
            help="默认显示最新一期 Payroll，可切换查询历史账期。"
        )
        
        if input_emp_id:
            # 过滤工号数据
            emp_all_df = df[df["工号"] == input_emp_id]
            
            if emp_all_df.empty:
                st.error(f"❌ 未找到工号 **{input_emp_id}** 的记录，请核对工号是否输入正确。")
            else:
                emp_name = emp_all_df["员工姓名"].iloc[0] if "员工姓名" in emp_all_df.columns else "员工"
                st.success(f"欢迎，**{emp_name}**（工号: {input_emp_id}）")
                
                # 过滤当前选择的 Payroll 编号数据
                emp_payroll_df = emp_all_df[emp_all_df["Payroll编号"] == selected_payroll].copy()
                
                # 提示当前是否为最新账期
                if selected_payroll == latest_payroll:
                    st.info(f"📅 当前展示：**第 {selected_payroll} 期 Payroll**（最新账期）")
                else:
                    st.warning(f"📜 当前展示：**第 {selected_payroll} 期 Payroll**（历史账期）")
                
                if emp_payroll_df.empty:
                    st.info(f"第 {selected_payroll} 期 Payroll 中暂无您的工时记录。")
                else:
                    # 计算核心工时指标
                    total_hours = emp_payroll_df["工作小时"].sum()
                    work_days = emp_payroll_df["日期"].nunique()
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("本期出勤天数", f"{work_days} 天")
                    col2.metric("本期累计工作小时", f"{total_hours:.1f} 小时")
                    col3.metric("当前查询账期", f"第 {selected_payroll} 期")
                    
                    st.markdown("---")
                    
                    # 展示每日工时与项目明细（不含薪资）
                    st.subheader(f"📋 第 {selected_payroll} 期每日工作小时与项目明细")
                    
                    display_cols = ["日期", "工作项目", "工作小时"]
                    if "备注" in emp_payroll_df.columns:
                        display_cols.append("备注")
                        
                    st.dataframe(
                        emp_payroll_df[display_cols].sort_values(by="日期", ascending=True),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # 可视化柱状图（每日工时分布）
                    st.subheader("📊 每日工作小时分布")
                    st.bar_chart(data=emp_payroll_df, x="日期", y="工作小时")
                    
                    st.markdown("---")
                    
                    # --- 工时核对与异常反馈区域 ---
                    st.subheader("💬 工时异常问题反馈")
                    st.caption("如果您对以上工时统计有异议或遗漏（如漏记算工时、项目不符等），请在下方提交反馈。")
                    
                    with st.form(key="feedback_form", clear_on_submit=True):
                        feedback_date = st.text_input("有问题的日期（例如：2026-07-15）：")
                        issue_type = st.selectbox("问题类型：", ["工时数有误", "遗漏天数未录入", "工作项目与实际不符", "其他"])
                        feedback_text = st.text_area("请详细说明情况：", placeholder="例如：7月15日实际在某工地工作了8.5小时，表格中只有6小时...")
                        
                        submit_btn = st.form_submit_button(label="提交反馈")
                        
                        if submit_btn:
                            if not feedback_text.strip():
                                st.warning("请填写具体的反馈说明。")
                            else:
                                st.success("✅ 反馈提交成功！管理人员核对后会及时为您修正工时。")
                                # 提示：生产环境中可将此反馈记录写入数据库或发送通知
        else:
            st.info("👈 请在左侧侧边栏输入您的**工号**，即可查看您的工时明细。")
