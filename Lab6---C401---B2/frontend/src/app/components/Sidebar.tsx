"use client";

import { Student } from "../page";

interface SidebarProps {
  students: Student[];
  activeStudentId: string;
  awaitingStudentId: boolean;
  onPickSuggestion: (question: string) => void;
  onClearChat: () => void;
  onClearStudentContext: () => void;
}

const SUGGESTIONS = [
  "Xin chao, ban co the ho tro gi cho toi?",
  "Lich hoc tuan nay",
  "Xem diem hoc ky 1",
  "Lich thi cuoi ky",
  "Kiem tra hoc phi cua toi",
  "Quy che dang ky tin chi",
];

export default function Sidebar({
  students,
  activeStudentId,
  awaitingStudentId,
  onPickSuggestion,
  onClearChat,
  onClearStudentContext,
}: SidebarProps) {
  return (
    <aside className="flex w-full flex-col gap-4 lg:w-[340px] xl:w-[360px]">
      <section className="overflow-hidden rounded-[28px] border border-[#d8c9b2] bg-[linear-gradient(160deg,#1c3943_0%,#234955_46%,#355f5c_100%)] text-[#f8f2e9] shadow-[0_18px_55px_rgba(19,49,59,0.2)]">
        <div className="px-5 pb-6 pt-5">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[rgba(255,249,239,0.16)] text-base font-semibold tracking-[0.2em] text-[#fff6ea]">
              SA
            </div>
            <div>
              <h2 className="text-xl text-[#fff7ef]">Student Assistant</h2>
              <p className="text-sm text-[#d9e5df]">
                Tra loi mem mai, tra cuu dung luc
              </p>
            </div>
          </div>

          <div className="mt-5 rounded-[22px] border border-[rgba(255,244,228,0.16)] bg-[rgba(255,249,239,0.1)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#f5cda9]">
              Trang thai phien
            </p>
            <p className="mt-2 text-sm leading-6 text-[#f7eee2]">
              {awaitingStudentId
                ? "He thong dang doi ban nhap MSSV de tiep tuc tra cuu thong tin ca nhan."
                : activeStudentId
                  ? `Dang ghi nho MSSV ${activeStudentId} cho cuoc tro chuyen hien tai.`
                  : "Ban cu hoi tu nhien. Neu can thong tin ca nhan, tro ly se hoi MSSV sau."}
            </p>
          </div>
        </div>
      </section>

      <section className="rounded-[28px] border border-[#dfd1ba] bg-[rgba(255,249,239,0.82)] p-5 shadow-[0_14px_40px_rgba(96,72,41,0.08)]">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#a06b48]">
              Hanh dong nhanh
            </p>
            <h3 className="mt-1 text-lg text-[#19333c]">Cau hoi goi y</h3>
          </div>
          {activeStudentId && (
            <button
              onClick={onClearStudentContext}
              className="rounded-full border border-[#d8c9b2] bg-white px-3 py-1.5 text-xs font-medium text-[#4d645e] transition hover:border-[#c96b43] hover:text-[#c96b43]"
            >
              Phien moi
            </button>
          )}
        </div>

        <div className="mt-4 grid gap-2">
          {SUGGESTIONS.map((question) => (
            <button
              key={question}
              disabled={awaitingStudentId}
              onClick={() => onPickSuggestion(question)}
              className="rounded-2xl border border-[#eadfca] bg-white px-4 py-3 text-left text-sm text-[#36515a] transition hover:-translate-y-0.5 hover:border-[#c96b43] hover:bg-[#fff6ee] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {question}
            </button>
          ))}
        </div>
      </section>

      <section className="flex-1 rounded-[28px] border border-[#dfd1ba] bg-[rgba(255,252,246,0.86)] p-5 shadow-[0_14px_40px_rgba(96,72,41,0.08)]">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#a06b48]">
          MSSV demo
        </p>
        <div className="mt-4 space-y-3">
          {students.map((student) => {
            const isActive = student.id === activeStudentId;
            return (
              <div
                key={student.id}
                className={`rounded-[22px] border px-4 py-3 transition ${
                  isActive
                    ? "border-[#c96b43] bg-[#fff1e8]"
                    : "border-[#eadfca] bg-white"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-[#19333c]">{student.name}</div>
                    <div className="mt-1 text-xs text-[#6c7b77]">{student.id}</div>
                  </div>
                  {isActive && (
                    <span className="rounded-full bg-[#c96b43] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-white">
                      Dang dung
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <button
        onClick={onClearChat}
        className="rounded-[24px] border border-[#d9c9b2] bg-white px-4 py-3 text-sm font-medium text-[#4d645e] shadow-[0_12px_32px_rgba(96,72,41,0.08)] transition hover:border-[#c96b43] hover:text-[#c96b43]"
      >
        Xoa lich su va tao hoi thoai moi
      </button>
    </aside>
  );
}
