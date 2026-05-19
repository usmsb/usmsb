/** GeneCapsulesPage - Gene Capsule 全局探索 */
import { Dna } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'

export default function GeneCapsulesPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">Gene Capsule</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="总胶囊" value="-" icon={Dna} color="primary" />
        <StatCard title="公开" value="-" icon={Dna} color="success" />
        <StatCard title="私有" value="-" icon={Dna} color="info" />
        <StatCard title="平均价值" value="-" icon={Dna} color="warning" />
      </div>
      <div className="bg-bg-secondary rounded-xl border border-border-primary p-8 text-center">
        <p className="text-text-muted">Gene Capsule 全局浏览功能开发中...</p>
      </div>
    </div>
  )
}
